"""
Tests for the multi-process org engine, per-task sessions and region-aware task planning.
"""

import contextvars
import inspect
import io
import re
import socket
import sqlite3
import threading
import zipfile

import boto3
import pytest

from aws_inventory.collector import (
    GLOBAL_SERVICES,
    SERVICE_CLIENT_MAP,
    get_available_services,
    get_collector_function,
    plan_collection_tasks,
    supported_regions,
)
from aws_inventory.engine import (
    AccountContextCredentials,
    AccountPlan,
    OrgScanEngine,
    UnitSession,
    _ClientFactory,
    _account_credentials,
    build_units,
    make_frozen_credentials,
    threads_for,
)
from aws_inventory.org import DEFAULT_ROLE_NAME, OrgInventoryOrchestrator
from aws_inventory.parallel import bounded_map


# ---------------------------------------------------------------------------
# Credentials context and unit sessions
# ---------------------------------------------------------------------------

def test_context_credentials_fail_closed_outside_account_context():
    """A request outside an account context must never be signed with some other identity."""
    creds = AccountContextCredentials()
    with pytest.raises(RuntimeError):
        creds.get_frozen_credentials()
    with pytest.raises(RuntimeError):
        _ = creds.access_key


def test_context_credentials_are_per_thread():
    """Two threads bound to two accounts see their own credentials through one object."""
    creds = AccountContextCredentials()
    seen = {}
    barrier = threading.Barrier(2)

    def worker(name):
        _account_credentials.set(make_frozen_credentials(f"AK-{name}", f"SK-{name}", f"TK-{name}"))
        barrier.wait()  # both contexts are set before either reads
        frozen = creds.get_frozen_credentials()
        seen[name] = (frozen.access_key, frozen.secret_key, frozen.token, creds.account_id)

    threads = [threading.Thread(target=worker, args=(n,)) for n in ("a", "b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert seen == {"a": ("AK-a", "SK-a", "TK-a", None), "b": ("AK-b", "SK-b", "TK-b", None)}


def test_worker_factory_never_loads_ambient_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AMBIENT")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "AMBIENT")
    creds = _ClientFactory("us-east-1").session.get_credentials()
    assert isinstance(creds, AccountContextCredentials)
    with pytest.raises(RuntimeError):
        creds.get_frozen_credentials()


def test_unit_session_reuses_clients_then_closes():
    session = UnitSession(_ClientFactory("us-east-1"))
    a = session.client("sqs", region_name="eu-west-1")
    assert session.client("sqs", region_name="eu-west-1") is a
    assert session.client("iam") is session.client("iam", region_name="us-east-1")
    session.close()
    assert session.client("sqs", region_name="eu-west-1") is not a


def test_build_units_groups_regional_tasks_and_splits_global_ones():
    def plan(acct, tasks):
        return AccountPlan(account_id=acct, credentials=(acct, "s", None), service_list=[],
                           region_list=["eu-west-1"], regions_filtered=False, tasks=tasks)
    plans = [plan(f"a{i}", [("iam", None), ("ec2", "eu-west-1")]) for i in range(10)]
    plans.append(plan("opt-in", [("ec2", "me-south-1")]))
    units = build_units(plans, unit_size=4)
    iam = [u for u in units if u[0] == "iam"]
    ec2 = [u for u in units if u[0] == "ec2" and u[1] == "eu-west-1"]
    assert len(iam) == 10 and all(len(u[2]) == 1 for u in iam)
    assert [len(u[2]) for u in ec2] == [4, 4, 2]
    assert [u for u in units if u[1] == "me-south-1"][0][2][0][0] == "opt-in"
    # every task appears exactly once
    flat = [(u[0], u[1], e[0]) for u in units for e in u[2]]
    assert len(flat) == len(set(flat)) == 21
    assert units[0][0] == "iam"  # global (long) tasks first


def test_bounded_map_propagates_context_and_order():
    var = contextvars.ContextVar("test_var", default=None)
    var.set("account-1")
    out = bounded_map(lambda i: (i, var.get(), threading.current_thread().name), range(20), max_workers=4)
    assert [o[0] for o in out] == list(range(20))
    assert {o[1] for o in out} == {"account-1"}
    assert len({o[2] for o in out}) > 1  # actually ran on pool threads


# ---------------------------------------------------------------------------
# Task planning
# ---------------------------------------------------------------------------

def test_service_client_map_matches_collectors():
    """Region filtering looks services up by client name: keep the map in sync with the code."""
    for service in get_available_services():
        source = inspect.getsource(inspect.getmodule(get_collector_function(service)))
        clients = re.findall(r"\.client\(\s*['\"]([a-z0-9-]+)['\"]", source)
        assert clients, service
        assert SERVICE_CLIENT_MAP.get(service, service) == clients[0], service


def test_supported_regions_filters_only_known_regions():
    # Device Farm only exists in us-west-2
    assert supported_regions("devicefarm", ["us-east-1", "us-west-2"]) == ["us-west-2"]
    # A region botocore has never heard of is always kept (outdated botocore must not hide data)
    assert supported_regions("devicefarm", ["xx-future-1"]) == ["xx-future-1"]
    # vpc is looked up through its ec2 client name
    assert supported_regions("vpc", ["us-east-1", "eu-west-3"]) == ["us-east-1", "eu-west-3"]


def test_plan_collection_tasks_order_and_global_handling():
    tasks = plan_collection_tasks(["ec2", "iam", "s3", "devicefarm"], ["us-east-1", "us-west-2"], False)
    assert tasks[:2] == [("iam", None), ("s3", None)]  # long single tasks first
    assert ("devicefarm", "us-west-2") in tasks
    assert ("devicefarm", "us-east-1") not in tasks
    assert ("ec2", "us-east-1") in tasks and ("ec2", "us-west-2") in tasks

    # With an explicit region filter, global services follow their control-plane region
    filtered = plan_collection_tasks(["iam", "networkmanager", "ec2"], ["eu-west-1"], True)
    assert filtered == [("ec2", "eu-west-1")]
    assert ("networkmanager", None) in plan_collection_tasks(["networkmanager"], ["us-west-2"], True)
    assert set(GLOBAL_SERVICES) >= {"iam", "networkmanager"}


# ---------------------------------------------------------------------------
# Engine behaviour (real worker processes)
# ---------------------------------------------------------------------------

def test_engine_reports_prepare_failures_and_empty_plans():
    done = []

    def prepare(acct):
        if acct["id"] == "bad":
            raise PermissionError("AccessDenied")
        return AccountPlan(account_id=acct["id"], credentials=("a", "b", None),
                           service_list=[], region_list=[], regions_filtered=True, tasks=[])

    engine = OrgScanEngine(
        processes=1, threads_per_process=1, max_accounts_in_flight=2, default_region="us-east-1",
        prepare_account=prepare,
        on_account_done=lambda acct, result, error, elapsed: done.append((acct["id"], result, error)),
    )
    engine.run([{"id": "good"}, {"id": "bad"}])
    by_id = {d[0]: d for d in done}
    assert by_id["good"][1]["metadata"]["resource_count"] == 0
    assert by_id["bad"][1] is None and "AccessDenied" in by_id["bad"][2]


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def moto_server(monkeypatch):
    server_mod = pytest.importorskip("moto.server")
    port = _free_port()
    server = server_mod.ThreadedMotoServer(ip_address="127.0.0.1", port=port, verbose=False)
    server.start()
    endpoint = f"http://127.0.0.1:{port}"
    # Environment is inherited by the spawned worker processes
    monkeypatch.setenv("AWS_ENDPOINT_URL", endpoint)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    for var in ("AWS_PROFILE", "AWS_SESSION_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    yield endpoint
    server.stop()


def _member_session(root, account_id):
    creds = root.client("sts").assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{DEFAULT_ROLE_NAME}", RoleSessionName="seed"
    )["Credentials"]
    return boto3.Session(aws_access_key_id=creds["AccessKeyId"], aws_secret_access_key=creds["SecretAccessKey"],
                         aws_session_token=creds["SessionToken"], region_name="us-east-1")


def _zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.py", "def handler(e, c):\n    return 1\n")
    return buf.getvalue()


def test_org_scan_end_to_end_isolates_accounts(moto_server, tmp_path):
    """Run the real multi-process engine against several accounts in moto.

    One client serves several accounts in a row inside a work unit, so this proves
    every request is signed for the account whose task issued it: each account must see
    exactly its own queues, topics and Lambda tags, and nothing from the others.
    """
    root = boto3.Session(region_name="us-east-1")
    mgmt_id = root.client("sts").get_caller_identity()["Account"]
    members = ["111111111111", "222222222222", "333333333333", "444444444444"]

    expected = {}
    for acct_id, session in [(mgmt_id, root)] + [(m, _member_session(root, m)) for m in members]:
        names = set()
        for region in ("us-east-1", "eu-west-1"):
            q = f"q-{acct_id}-{region}"
            session.client("sqs", region_name=region).create_queue(QueueName=q)
            t = f"t-{acct_id}-{region}"
            session.client("sns", region_name=region).create_topic(Name=t)
            names.update({q, t})
        role_arn = session.client("iam").create_role(
            RoleName="fn-role", AssumeRolePolicyDocument="{}")["Role"]["Arn"]
        fn = f"fn-{acct_id}"
        session.client("lambda", region_name="eu-west-1").create_function(
            FunctionName=fn, Runtime="python3.12", Role=role_arn, Handler="index.handler",
            Code={"ZipFile": _zip_bytes()}, Tags={"owner": acct_id},
        )
        names.add(fn)
        expected[acct_id] = names

    db_file = str(tmp_path / "org.db")
    orchestrator = OrgInventoryOrchestrator(
        root_session=root,
        session_policy=None,
        processes=2,
        threads_per_process=4,
        account_concurrency=3,
        services=["sqs", "sns", "lambda"],
        regions=["us-east-1", "eu-west-1"],
        db_path=db_file,
        quiet=True,
    )
    accounts = [{"id": mgmt_id, "name": "mgmt", "is_management": True}] + [
        {"id": m, "name": f"member-{m[:3]}", "is_management": False} for m in members
    ]
    summary = orchestrator.execute(accounts)
    assert summary["failed_accounts"] == 0
    assert summary["completed_accounts"] == len(accounts)

    conn = sqlite3.connect(db_file)
    rows = conn.execute("SELECT account_id, service, name, tags FROM resources WHERE is_current=1").fetchall()
    conn.close()

    found = {}
    for account_id, service, name, tags in rows:
        if service in ("sqs", "sns") and name.startswith(("q-", "t-")) or service == "lambda" and name.startswith("fn-"):
            found.setdefault(account_id, set()).add(name)
        if service == "lambda" and name.startswith("fn-"):
            # Tags must be fetched with the scanned account's credentials
            assert account_id in (tags or ""), (account_id, name, tags)
    assert found == expected


def test_concurrency_budget_is_total_not_per_process():
    assert threads_for(256, 4) == 64
    assert threads_for(128, 12) == 11
    assert threads_for(4, 8) == 1


def test_unit_session_closes_connections(moto_server):
    """No idle socket may outlive its unit (they used to pile up past macOS' 256-file limit)."""
    session = UnitSession(_ClientFactory("us-east-1"))
    token = _account_credentials.set(make_frozen_credentials("testing", "testing", None))
    try:
        client = session.client("sqs", region_name="us-east-1")
        client.list_queues()
    finally:
        _account_credentials.reset(token)
    pools = client._endpoint.http_session._manager.pools
    assert len(pools) == 1
    session.close()
    assert len(pools) == 0


def test_transient_errors_are_recorded_for_retry_but_not_permanent_ones():
    from types import SimpleNamespace
    from aws_inventory.engine import _after_call, _after_call_error, _task_transient

    seen = []
    token = _task_transient.set(seen)
    try:
        ok = SimpleNamespace(status_code=200)
        _after_call(http_response=ok, parsed={"Items": []}, model=SimpleNamespace(name="ListThings"))
        _after_call(http_response=SimpleNamespace(status_code=400),
                    parsed={"Error": {"Code": "AccessDeniedException"}}, model=SimpleNamespace(name="ListA"))
        assert seen == []  # success and permanent errors are not retried
        _after_call(http_response=SimpleNamespace(status_code=400),
                    parsed={"Error": {"Code": "ThrottlingException"}}, model=SimpleNamespace(name="ListB"))
        _after_call(http_response=SimpleNamespace(status_code=503), parsed={}, model=SimpleNamespace(name="ListC"))
        _after_call_error(exception=TimeoutError())
        assert seen == ["ListB: ThrottlingException", "ListC: 503", "TimeoutError"]
    finally:
        _task_transient.reset(token)
