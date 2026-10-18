"""
Multi-process collection engine used by `awsmap org`.

What limits an org scan (measured on a real 103-account organization)
---------------------------------------------------------------------
A full account is ~2,300 (service, region) tasks of ~2.7 API calls each. The
binding limit is not CPU and not AWS throttling (a few retries out of thousands
of calls), it is **new TLS connections**: opening a connection per call caps out
at ~50 calls/s whatever the thread count, while reused keep-alive connections
reach ~440 calls/s with the same threads. Every earlier engine (the original one
included) opened a fresh connection for every task.

How this engine works
---------------------
* Accounts are processed in batches. For a batch, the tasks of the same
  (service, region) across up to UNIT_SIZE accounts form one *work unit*.
* A unit runs on one thread, over one client and therefore one kept-alive HTTPS
  connection: the first task pays the TLS handshake, the next ones reuse it. The
  credentials used to sign each request come from the account being processed
  (a ContextVar), and any call outside an account context raises instead of using
  an ambient identity.
* The unit's clients are closed when the unit ends, so open sockets stay close to
  the number of threads (an earlier version kept every client's connections
  open forever and ran out of file descriptors).
* Worker processes pull units from ONE shared queue, so a slow service or region
  only holds the thread running it. The next batch is dispatched while the
  previous one drains, so threads never idle between batches.
* Each worker parses service models once and shares one TLS context, which keeps
  CPU per call low enough for a laptop to drive hundreds of concurrent calls.
"""

import contextvars
import heapq
import math
import multiprocessing
import os
import pickle
import queue
import signal
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

import boto3
import botocore.session
from botocore.config import Config
from botocore.credentials import Credentials, ReadOnlyCredentials

from aws_inventory.collector import run_collection_task

# Concurrent work units (threads) across ALL worker processes. Each one holds about
# one HTTPS connection, so this is what the local network sees.
DEFAULT_TOTAL_CONCURRENCY = 256

# Accounts sharing one work unit (and one connection) per (service, region).
UNIT_SIZE = 8


def default_process_count() -> int:
    """Worker processes to use when the user does not choose: one per core, capped."""
    return max(1, min(os.cpu_count() or 2, 6))


def threads_for(total_concurrency: int, processes: int) -> int:
    """Split a total concurrency budget evenly across worker processes."""
    return max(1, math.ceil(total_concurrency / max(1, processes)))


def raise_open_file_limit(target: int = 4096) -> None:
    """Lift the soft open-file limit (256 by default on macOS) towards the hard limit."""
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        wanted = target if hard == resource.RLIM_INFINITY else min(target, hard)
        if soft != resource.RLIM_INFINITY and soft < wanted:
            resource.setrlimit(resource.RLIMIT_NOFILE, (wanted, hard))
    except Exception:
        pass  # not available (Windows) or not permitted: keep the current limit


# ---------------------------------------------------------------------------
# Per-thread account credentials
# ---------------------------------------------------------------------------

_account_credentials: contextvars.ContextVar = contextvars.ContextVar(
    "awsmap_account_credentials", default=None
)


class AccountContextCredentials(Credentials):
    """Credentials whose values come from the calling thread's account context.

    botocore asks the credentials object for frozen credentials every time it signs
    a request, in the thread that makes the call. Returning the values bound to the
    current context lets one client (and its connection) serve several accounts
    one after the other. bounded_map copies the context into its pool threads.
    """

    def __init__(self) -> None:  # noqa: D107 - values are dynamic, nothing to store
        self.method = "awsmap-account-context"

    @staticmethod
    def _current() -> ReadOnlyCredentials:
        creds = _account_credentials.get()
        if creds is None:
            raise RuntimeError("AWS API call issued outside of an account context")
        return creds

    @property
    def access_key(self) -> str:
        return self._current().access_key

    @property
    def secret_key(self) -> str:
        return self._current().secret_key

    @property
    def token(self) -> Optional[str]:
        return self._current().token

    @property
    def account_id(self) -> None:
        # Never expose an account ID: a client serves several accounts, and an
        # account-specific endpoint (e.g. DynamoDB) must not be baked into one.
        return None

    def get_frozen_credentials(self) -> ReadOnlyCredentials:
        return self._current()


def make_frozen_credentials(access_key: str, secret_key: str, token: Optional[str]) -> ReadOnlyCredentials:
    """Build botocore ReadOnlyCredentials across botocore versions (3 or 4 fields)."""
    values = [access_key, secret_key, token, None][: len(ReadOnlyCredentials._fields)]
    return ReadOnlyCredentials(*values)


class _ContextCredentialResolver:
    """Stands in for botocore's credential resolver: never loads an ambient identity."""

    def __init__(self) -> None:
        self._credentials = AccountContextCredentials()

    def load_credentials(self) -> Credentials:
        return self._credentials


# ---------------------------------------------------------------------------
# Worker process
# ---------------------------------------------------------------------------

_tls_lock = threading.Lock()
_tls_contexts: Dict[str, Any] = {}


def _share_tls_context() -> None:
    """Load the CA bundle once per worker process instead of once per TLS connection.

    botocore passes the CA bundle path to urllib3 for every new connection, and
    urllib3 then re-parses the whole bundle (measured ~20 ms of CPU each time). A
    scan opens a new connection per task, so this alone was a large part of the
    CPU cost. Here every HTTPS pool in the process gets one shared, pre-loaded
    SSLContext and no per-connection path. Certificate and hostname verification
    are unchanged. Sessions with a proxy CA bundle or a client certificate keep
    botocore's default behaviour. Only ever called inside worker processes.
    """
    from botocore import httpsession

    if getattr(httpsession.URLLib3Session, "_awsmap_shared_tls", False):
        return
    original_get_context = httpsession.URLLib3Session._get_ssl_context
    original_setup_cert = httpsession.URLLib3Session._setup_ssl_cert

    def _shareable(session: Any) -> bool:
        settings = getattr(getattr(session, "_proxy_config", None), "settings", None) or {}
        return bool(session._verify) and not getattr(session, "_cert_file", None) and not (
            settings.get("proxy_ca_bundle") or settings.get("proxy_client_cert"))

    def _get_ssl_context(self: Any) -> Any:
        if not _shareable(self):
            return original_get_context(self)
        path = httpsession.get_cert_path(self._verify)
        with _tls_lock:
            context = _tls_contexts.get(path)
            if context is None:
                context = httpsession.create_urllib3_context()
                context.load_verify_locations(cafile=path)
                _tls_contexts[path] = context
        self._awsmap_tls_path = path
        return context

    def _setup_ssl_cert(self: Any, conn: Any, url: str, verify: Any) -> None:
        if (url.lower().startswith("https") and verify
                and getattr(self, "_awsmap_tls_path", None) == httpsession.get_cert_path(verify)):
            conn.cert_reqs = "CERT_REQUIRED"
            conn.ca_certs = None  # already loaded in the shared context
            return
        original_setup_cert(self, conn, url, verify)

    httpsession.URLLib3Session._get_ssl_context = _get_ssl_context
    httpsession.URLLib3Session._setup_ssl_cert = _setup_ssl_cert
    httpsession.URLLib3Session._awsmap_shared_tls = True


class _ClientFactory:
    """Creates clients from one botocore session per worker process.

    The session caches parsed service models and endpoint data, which is most of
    the cost of creating a client. Creation is serialized: it is pure CPU (the GIL
    serializes it anyway) and boto3 sessions have known races on concurrent use.
    """

    def __init__(self, default_region: str) -> None:
        core = botocore.session.Session()
        core.register_component("credential_provider", _ContextCredentialResolver())
        self.session = boto3.Session(botocore_session=core, region_name=default_region)
        self.default_region = default_region
        config_kwargs: Dict[str, Any] = {"max_pool_connections": 10}
        if "account_id_endpoint_mode" in getattr(Config, "OPTION_DEFAULTS", {}):
            config_kwargs["account_id_endpoint_mode"] = "disabled"
        self._config = Config(**config_kwargs)
        self._lock = threading.Lock()

    def create(self, service_name: str, region_name: Optional[str],
               endpoint_url: Optional[str], **kwargs: Any) -> Any:
        kwargs["config"] = self._config.merge(kwargs["config"]) if "config" in kwargs else self._config
        with self._lock:
            return self.session.client(service_name, region_name=region_name,
                                       endpoint_url=endpoint_url, **kwargs)


class UnitSession:
    """The subset of boto3.Session that collectors use, for one work unit.

    Collectors only call ``session.client(name, region_name=..., endpoint_url=...)``.
    Clients are created on first use, reused for every account of the unit (so their
    keep-alive connections are reused too), and closed when the unit ends.
    """

    def __init__(self, factory: _ClientFactory) -> None:
        self._factory = factory
        self._clients: Dict[Tuple[str, Optional[str], Optional[str]], Any] = {}
        self._extra: List[Any] = []
        self._lock = threading.Lock()

    @property
    def region_name(self) -> Optional[str]:
        return self._factory.default_region

    @property
    def profile_name(self) -> Optional[str]:
        return None

    def client(self, service_name: str, region_name: Optional[str] = None,
               endpoint_url: Optional[str] = None, **kwargs: Any) -> Any:
        region = region_name or self._factory.default_region
        if kwargs:
            client = self._factory.create(service_name, region, endpoint_url, **kwargs)
            with self._lock:
                self._extra.append(client)
            return client
        key = (service_name, region, endpoint_url)
        with self._lock:
            client = self._clients.get(key)
        if client is None:
            client = self._factory.create(service_name, region, endpoint_url)
            with self._lock:
                client = self._clients.setdefault(key, client)
        return client

    def get_available_regions(self, *args: Any, **kwargs: Any) -> List[str]:
        return self._factory.session.get_available_regions(*args, **kwargs)

    def close(self) -> None:
        with self._lock:
            clients = list(self._clients.values()) + self._extra
            self._clients, self._extra = {}, []
        for client in clients:
            try:
                client.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Transient-failure detection
# ---------------------------------------------------------------------------

# Collectors swallow API errors (`except Exception: pass`), so a throttled or
# timed-out call would silently drop resources. Every API response in a worker is
# inspected here instead; a task that hit a transient error is re-run.
_TRANSIENT_CODES = frozenset({
    "Throttling", "ThrottlingException", "ThrottledException", "RequestThrottledException",
    "TooManyRequestsException", "ProvisionedThroughputExceededException", "RequestLimitExceeded",
    "BandwidthLimitExceeded", "SlowDown", "PriorRequestNotComplete", "EC2ThrottledException",
    "RequestTimeout", "RequestTimeoutException", "InternalError", "InternalFailure",
    "InternalServerError", "InternalServerException", "ServiceUnavailable",
    "ServiceUnavailableException", "TransactionInProgressException",
})

_task_transient: contextvars.ContextVar = contextvars.ContextVar("awsmap_task_transient", default=None)

# Permission errors are permanent: never retried, but the data they hide is reported.
_DENIED_CODES = frozenset({
    "AccessDenied", "AccessDeniedException", "UnauthorizedOperation", "UnauthorizedAccess",
    "AuthorizationError", "Forbidden",
})

_task_denied: contextvars.ContextVar = contextvars.ContextVar("awsmap_task_denied", default=None)


def _record_transient(reason: str) -> None:
    errors = _task_transient.get()
    if errors is not None:
        errors.append(reason)


def _record_denied(reason: str) -> None:
    denied = _task_denied.get()
    if denied is not None and reason not in denied:
        denied.append(reason)


# Failures to even reach an endpoint. When every account fails this way on the same
# (service, region) and none succeeds, the service is simply not offered there
# (no DNS name), which botocore's endpoint data does not always know.
_CONNECT_FAILURES = frozenset({"EndpointConnectionError", "ProxyConnectionError", "ConnectTimeoutError"})
DEAD_ENDPOINT_THRESHOLD = 3


def _after_call(http_response: Any = None, parsed: Any = None, model: Any = None, **kwargs: Any) -> None:
    status = getattr(http_response, "status_code", 200) or 200
    code = ((parsed or {}).get("Error") or {}).get("Code") if isinstance(parsed, dict) else None
    if status >= 500 or status == 429 or (code in _TRANSIENT_CODES):
        _record_transient(f"{getattr(model, 'name', '?')}: {code or status}")
    elif code in _DENIED_CODES:
        _record_denied(f"{getattr(model, 'name', '?')}: {code}")


def _after_call_error(exception: Any = None, **kwargs: Any) -> None:
    # Raised without an HTTP response: connection reset, read timeout, DNS failure...
    _record_transient(type(exception).__name__)


# Unit message: (service, region, [(account_id, (access_key, secret_key, token),
#                                   region_list, regions_filtered), ...])
# Result message: pickled (account_id, service, region, resources, elapsed, error,
# transient_errors, denied_calls), one per task. Workers pickle results themselves: if multiprocessing's feeder
# thread failed to pickle a message it would drop it silently and the parent would
# wait forever.


def _worker_main(task_queue: Any, result_queue: Any, threads: int, default_region: str) -> None:
    """Entry point of a worker process: run work units on a pool of threads."""
    # The parent owns Ctrl+C handling and terminates workers itself.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    raise_open_file_limit()
    _share_tls_context()
    factory = _ClientFactory(default_region)
    factory.session.events.register("after-call", _after_call)
    factory.session.events.register("after-call-error", _after_call_error)

    def run_unit(service: str, region: Optional[str], entries: List[Tuple]) -> None:
        session = UnitSession(factory)
        try:
            for account_id, creds, region_list, regions_filtered in entries:
                token = _account_credentials.set(make_frozen_credentials(*creds))
                transient: List[str] = []
                transient_token = _task_transient.set(transient)
                denied: List[str] = []
                denied_token = _task_denied.set(denied)
                start = time.time()
                try:
                    resources, _ = run_collection_task(
                        session, service, region, account_id, region_list, regions_filtered)
                    error = None
                except Exception as e:  # collectors swallow API errors; this is a bug guard
                    resources, error = [], f"{type(e).__name__}: {e}"
                finally:
                    _task_denied.reset(denied_token)
                    _task_transient.reset(transient_token)
                    _account_credentials.reset(token)
                elapsed = time.time() - start
                try:
                    payload = pickle.dumps((account_id, service, region, resources, elapsed, error,
                                            transient[:3], denied[:5]), protocol=pickle.HIGHEST_PROTOCOL)
                except Exception as e:
                    payload = pickle.dumps((account_id, service, region, [], elapsed,
                                            f"unpicklable result: {type(e).__name__}: {e}", [], []))
                result_queue.put(payload)
        finally:
            session.close()

    def loop() -> None:
        while True:
            message = task_queue.get()
            if message is None:
                return
            run_unit(*message)

    pool = [threading.Thread(target=loop, name=f"awsmap-worker-{i}", daemon=True) for i in range(threads)]
    for t in pool:
        t.start()
    for t in pool:
        t.join()


# ---------------------------------------------------------------------------
# Parent-side orchestration
# ---------------------------------------------------------------------------

@dataclass
class AccountPlan:
    """Everything needed to dispatch one account's tasks to the workers."""
    account_id: str
    credentials: Tuple[str, str, Optional[str]]
    service_list: List[str]
    region_list: List[str]
    regions_filtered: bool
    tasks: List[Tuple[str, Optional[str]]]


@dataclass
class _AccountState:
    account: Dict[str, Any]
    plan: AccountPlan
    started: float
    remaining: int
    resources: List[Dict[str, Any]] = field(default_factory=list)
    task_errors: int = 0
    # (service, region, reason) for tasks that ended in error: their data is missing
    incomplete: List[Tuple[str, Optional[str], str]] = field(default_factory=list)
    attempts: Dict[Tuple[str, Optional[str]], int] = field(default_factory=dict)


class WorkerDiedError(RuntimeError):
    """A worker process exited unexpectedly; its in-flight tasks are lost."""


def build_units(plans: List[AccountPlan], unit_size: int = UNIT_SIZE) -> List[Tuple]:
    """Group a batch's tasks into work units of the same (service, region).

    Global tasks (region None: IAM, S3, Organizations...) are long and per-account,
    so they stay one account per unit. Order follows the plans (global/S3 first),
    so the longest tasks start first.
    """
    groups: Dict[Tuple[str, Optional[str]], List[Tuple]] = {}
    order: List[Tuple[str, Optional[str]]] = []
    for plan in plans:
        for service, region in plan.tasks:
            key = (service, region)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append((plan.account_id, plan.credentials, plan.region_list, plan.regions_filtered))
    units: List[Tuple] = []
    for service, region in order:
        entries = groups[(service, region)]
        size = 1 if region is None else max(1, unit_size)
        for i in range(0, len(entries), size):
            units.append((service, region, entries[i:i + size]))
    return units


class OrgScanEngine:
    """Runs collection for many accounts on a pool of worker processes.

    Args:
        processes: Number of worker processes.
        threads_per_process: Concurrent work units per worker process.
        max_accounts_in_flight: Batch size (accounts prepared and dispatched together).
        default_region: Region for clients created without one (IAM, S3...).
        prepare_account: fn(account) -> AccountPlan; assumes the role and plans tasks.
            Runs on daemon threads in the parent. May raise to fail the account.
        on_account_done: fn(account, result_or_None, error_or_None, elapsed_seconds),
            always called from the thread that called run().
        on_heartbeat: optional fn(stats) called about every heartbeat_seconds while
            no account has completed.
    """

    def __init__(
        self,
        processes: int,
        threads_per_process: int,
        max_accounts_in_flight: int,
        default_region: str,
        prepare_account: Callable[[Dict[str, Any]], AccountPlan],
        on_account_done: Callable[[Dict[str, Any], Optional[Dict[str, Any]], Optional[str], float], None],
        on_heartbeat: Optional[Callable[[Dict[str, int]], None]] = None,
        heartbeat_seconds: float = 15.0,
        unit_size: int = UNIT_SIZE,
    ) -> None:
        self.processes = max(1, processes)
        self.threads_per_process = max(1, threads_per_process)
        self.batch_size = max(1, max_accounts_in_flight)
        self.default_region = default_region
        self.prepare_account = prepare_account
        self.on_account_done = on_account_done
        self.on_heartbeat = on_heartbeat
        self.heartbeat_seconds = heartbeat_seconds
        self.unit_size = max(1, unit_size)
        self.max_task_retries = 3
        # Delay before each re-run: throttling needs time to clear.
        self.retry_delays = (15.0, 45.0, 90.0)
        self.tasks_retried = 0
        self.tasks_failed_transient = 0
        # (account_id, service, region, last transient error) for tasks that never succeeded
        self.failed_tasks: List[Tuple[str, str, Optional[str], str]] = []
        # (service, "Operation: ErrorCode") -> account ids that were denied
        self.denied_calls: Dict[Tuple[str, str], set] = {}
        # (service, region) endpoints that no account could connect to: skipped.
        self.dead_endpoints: set = set()
        self._endpoint_connect_failures: Dict[Tuple[str, Optional[str]], int] = {}
        self._endpoint_ok: set = set()
        self.tasks_done = 0
        self.tasks_total = 0
        self.accounts_done = 0
        # service -> [total seconds, slowest task seconds, slowest region, task count]
        self.service_timings: Dict[str, List[Any]] = {}

    def run(self, accounts: List[Dict[str, Any]]) -> None:
        if not accounts:
            return
        raise_open_file_limit()
        # spawn everywhere: fork() of a process with live threads is unsafe, and
        # spawn is already the default on macOS.
        ctx = multiprocessing.get_context("spawn")
        task_queue = ctx.Queue()
        result_queue = ctx.Queue()
        workers = [
            ctx.Process(
                target=_worker_main,
                args=(task_queue, result_queue, self.threads_per_process, self.default_region),
                name=f"awsmap-worker-{i}",
                daemon=True,
            )
            for i in range(self.processes)
        ]
        for w in workers:
            w.start()

        total_threads = self.processes * self.threads_per_process
        pending: Deque[Dict[str, Any]] = deque(accounts)
        preparing: Dict[str, Dict[str, Any]] = {}
        prepared: "queue.Queue[Tuple[Dict[str, Any], Optional[AccountPlan], Optional[str]]]" = queue.Queue()
        batch_plans: List[Tuple[Dict[str, Any], AccountPlan]] = []
        active: Dict[str, _AccountState] = {}
        retry_heap: List[Tuple[float, int, Tuple]] = []  # (ready_at, seq, unit)
        retry_seq = 0

        def prepare(acct: Dict[str, Any]) -> None:
            # Daemon thread: a role assumption stuck on the network must never keep
            # the process alive after Ctrl+C.
            try:
                prepared.put((acct, self.prepare_account(acct), None))
            except Exception as e:
                prepared.put((acct, None, f"{type(e).__name__}: {e}" if str(e) else type(e).__name__))

        def finish(state: _AccountState) -> None:
            self.accounts_done += 1
            plan = state.plan
            elapsed = time.time() - state.started
            result = {
                "metadata": {
                    "account_id": plan.account_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                    "scan_duration_seconds": round(elapsed, 2),
                    "services_scanned": len(plan.service_list),
                    "services_scanned_list": plan.service_list,
                    "regions_scanned": len(plan.region_list),
                    "resource_count": len(state.resources),
                    "incomplete_tasks": [list(t) for t in state.incomplete],
                },
                "resources": state.resources,
            }
            self.on_account_done(state.account, result, None, elapsed)

        def dispatch_batch() -> None:
            now = time.time()
            plans = []
            for acct, plan in batch_plans:
                if self.dead_endpoints:
                    plan.tasks = [t for t in plan.tasks if t not in self.dead_endpoints]
                state = _AccountState(account=acct, plan=plan, started=now, remaining=len(plan.tasks))
                if not plan.tasks:
                    finish(state)
                    continue
                active[plan.account_id] = state
                plans.append(plan)
                self.tasks_total += len(plan.tasks)
            batch_plans.clear()
            for unit in build_units(plans, self.unit_size):
                task_queue.put(unit)

        last_progress = time.time()
        clean_exit = False
        try:
            while pending or preparing or batch_plans or active:
                # Prepare the next batch once the queue is close to draining, so the
                # threads go straight from one batch to the next.
                outstanding = self.tasks_total - self.tasks_done
                if (pending and not preparing and not batch_plans
                        and outstanding <= total_threads * self.unit_size):
                    for _ in range(min(self.batch_size, len(pending))):
                        acct = pending.popleft()
                        preparing[acct["id"]] = acct
                        threading.Thread(target=prepare, args=(acct,), name="awsmap-prepare",
                                         daemon=True).start()

                while True:
                    try:
                        acct, plan, prep_error = prepared.get_nowait()
                    except queue.Empty:
                        break
                    preparing.pop(acct["id"], None)
                    if plan is None:
                        self.on_account_done(acct, None, prep_error, 0.0)
                        last_progress = time.time()
                    else:
                        batch_plans.append((acct, plan))
                if batch_plans and not preparing:
                    dispatch_batch()

                now = time.time()
                while retry_heap and retry_heap[0][0] <= now:
                    task_queue.put(heapq.heappop(retry_heap)[2])

                # Collect results (block briefly, then drain whatever is ready).
                try:
                    message = result_queue.get(timeout=0.2)
                except queue.Empty:
                    message = None
                    dead = [w.name for w in workers if not w.is_alive()]
                    if dead:
                        raise WorkerDiedError(f"worker process(es) exited unexpectedly: {', '.join(dead)}")
                    if self.on_heartbeat and active and time.time() - last_progress >= self.heartbeat_seconds:
                        last_progress = time.time()
                        self.on_heartbeat({
                            "accounts_done": self.accounts_done,
                            "accounts_in_flight": len(active) + len(preparing),
                            "tasks_done": self.tasks_done,
                            "tasks_total": self.tasks_total,
                        })
                while message is not None:
                    account_id, service, region, resources, elapsed, error, transient, denied = pickle.loads(message)
                    state = active.get(account_id)
                    endpoint = (service, region)
                    if not transient:
                        self._endpoint_ok.add(endpoint)
                    elif all(reason in _CONNECT_FAILURES for reason in transient) and endpoint not in self._endpoint_ok:
                        count = self._endpoint_connect_failures.get(endpoint, 0) + 1
                        self._endpoint_connect_failures[endpoint] = count
                        if count >= DEAD_ENDPOINT_THRESHOLD:
                            self.dead_endpoints.add(endpoint)
                    if endpoint in self.dead_endpoints:
                        transient = []  # unreachable endpoint: nothing to retry or report per task
                    if transient and state is not None:
                        attempt = state.attempts.get((service, region), 0) + 1
                        state.attempts[(service, region)] = attempt
                        if attempt <= self.max_task_retries:
                            # Re-run the whole task later; discard this partial result.
                            self.tasks_retried += 1
                            plan = state.plan
                            delay = self.retry_delays[min(attempt, len(self.retry_delays)) - 1]
                            retry_seq += 1
                            heapq.heappush(retry_heap, (time.time() + delay, retry_seq, (
                                service, region,
                                [(account_id, plan.credentials, plan.region_list, plan.regions_filtered)])))
                            try:
                                message = result_queue.get_nowait()
                            except queue.Empty:
                                message = None
                            continue
                        self.tasks_failed_transient += 1
                        self.failed_tasks.append((account_id, service, region, transient[-1]))
                        if state is not None:
                            state.incomplete.append((service, region, transient[-1]))
                    for reason in denied:
                        self.denied_calls.setdefault((service, reason), set()).add(account_id)
                    self.tasks_done += 1
                    timing = self.service_timings.setdefault(service, [0.0, 0.0, None, 0])
                    timing[0] += elapsed
                    timing[3] += 1
                    if elapsed > timing[1]:
                        timing[1], timing[2] = elapsed, region
                    if state is not None:
                        state.resources.extend(resources)
                        if error:
                            state.task_errors += 1
                            state.incomplete.append((service, region, error))
                        state.remaining -= 1
                        if state.remaining == 0:
                            del active[account_id]
                            finish(state)
                            last_progress = time.time()
                    try:
                        message = result_queue.get_nowait()
                    except queue.Empty:
                        message = None
            # Tasks that failed before their endpoint was recognised as unreachable
            # are not missing data.
            self.failed_tasks = [f for f in self.failed_tasks if (f[1], f[2]) not in self.dead_endpoints]
            clean_exit = True
        finally:
            if clean_exit:
                for _ in range(total_threads):
                    task_queue.put(None)
                for w in workers:
                    w.join(timeout=10)
            for w in workers:
                if w.is_alive():
                    w.terminate()
            for w in workers:
                w.join(timeout=5)
            for q in (task_queue, result_queue):
                q.cancel_join_thread()
                q.close()
