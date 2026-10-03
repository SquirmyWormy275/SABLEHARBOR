"""Temporary fresh graph proofs for one guarded HTTP request.

Exact authoritative node bytes are read and verified once per unchanged
journal image in this request. A write, sidecar or file-identity change forces
another complete proof. Nothing survives request completion: no parsed JSON,
evidence, examination result, session authority or service outcome is cached.
"""

from contextvars import ContextVar
from threading import RLock

MAX_GRAPH_BYTES = 512 * 1024**2
_CURRENT = ContextVar("retained_request_integrity", default=None)


class RequestIntegrity:
    def __init__(self):
        self._entries = {}
        self._lock = RLock()
        self.closed = False
        self.fresh_graphs = 0
        self.graph_reuses = 0

    def get(self, key, stamp, roots):
        with self._lock:
            if self.closed:
                return None
            old = self._entries.get(key)
            if old is None or old["stamp"] != stamp or old["roots"] != frozenset(roots):
                return None
            self.graph_reuses += 1
            return {
                "nodes": dict(old["nodes"]),
                "proof": dict(old["proof"]),
                "roots": old["roots"],
            }

    def put(self, key, stamp, roots, graph):
        with self._lock:
            self.fresh_graphs += 1
            old = self._entries.pop(key, None)
            if old is not None:
                old["nodes"].clear()
                old["proof"].clear()
            if self.closed or sum(len(x[1]) for x in graph._nodes.values()) > MAX_GRAPH_BYTES:
                return
            self._entries[key] = {
                "stamp": stamp,
                "roots": frozenset(roots),
                "nodes": dict(graph._nodes),
                "proof": dict(graph._proof),
            }

    def close(self):
        with self._lock:
            for old in self._entries.values():
                old["nodes"].clear()
                old["proof"].clear()
            self._entries.clear()
            self.closed = True


def current():
    return _CURRENT.get()


def begin():
    scope = RequestIntegrity()
    return scope, _CURRENT.set(scope)


def finish(scope, token):
    try:
        scope.close()
    finally:
        _CURRENT.reset(token)
