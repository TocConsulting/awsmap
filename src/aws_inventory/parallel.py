"""
Bounded fan-out for per-resource enrichment calls inside a single collector.

Collectors such as IAM and S3 make several API calls per resource (tags, attached
policies, bucket settings...). Done one after the other, a large account turns that
single task into the long pole of the whole scan. bounded_map runs those calls on a
small, short-lived pool.

The caller's contextvars (which hold the account credentials during `awsmap org`
scans) are copied into every pool thread, so enrichment calls are always signed for
the same account as the collector that issued them.
"""

import contextvars
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, List, TypeVar

T = TypeVar("T")
R = TypeVar("R")

# Below this many items, threads cost more than they save.
_INLINE_THRESHOLD = 3


def bounded_map(fn: Callable[[T], R], items: Iterable[T], max_workers: int = 8) -> List[R]:
    """Apply fn to every item with at most max_workers threads, preserving order.

    fn is expected to handle its own per-item errors (as collectors already do);
    an exception escaping fn propagates to the caller.
    """
    items = list(items)
    if len(items) < _INLINE_THRESHOLD or max_workers <= 1:
        return [fn(item) for item in items]

    parent_context = contextvars.copy_context()

    def run(item: T) -> R:
        # A Context can only be entered by one thread at a time, so each call
        # runs in its own copy of the caller's context.
        return parent_context.copy().run(fn, item)

    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as pool:
        return list(pool.map(run, items))
