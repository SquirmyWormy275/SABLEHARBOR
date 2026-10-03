"""Canonical byte hashing with an optional, explicitly built native validator.

Raw JSON is never presumed canonical. The accelerator accepts only the exact
UTF-8 representation produced by Store.canonical. All other inputs preserve
the existing json.loads/canonical behavior, including legacy duplicate keys.
There is no source, state, evidence or validation cache in this module.
"""

from __future__ import annotations

import importlib
import json
import sys
import sysconfig
from pathlib import Path

from .store import DomainError, canonical

try:
    _native = importlib.import_module("enterprise.audit_suite._serialized_json_native")
except ModuleNotFoundError as error:
    if error.name != "enterprise.audit_suite._serialized_json_native":
        raise
    _native = None


def native_code_files():
    """Loaded executable and its reviewed source, for operator code pins.

    Importing this module never runs a compiler. A deployment without the
    optional local binary uses the original stdlib algorithm.
    """
    if _native is None:
        return {}
    path = Path(_native.__file__)
    if (
        path.name != "_serialized_json_native" + sysconfig.get_config_var("EXT_SUFFIX")
        or getattr(_native.__spec__, "name", None)
        != "enterprise.audit_suite._serialized_json_native"
        or Path(_native.__spec__.origin).resolve() != path.resolve()
    ):
        raise DomainError("Loaded native validator origin or interpreter ABI differs")
    return {
        path.name: path,
        "_serialized_json_native.c": Path(__file__).with_name("_serialized_json_native.c"),
    }


def canonical_bytes(serialized):
    """Return exactly canonical(json.loads(serialized)).encode(), or its error."""
    if _native is not None and type(serialized) is str:
        try:
            raw = serialized.encode("utf-8")
        except UnicodeEncodeError:
            pass  # Let the original decoder/encoder determine the failure.
        else:
            if _native.validate(raw, sys.get_int_max_str_digits()):
                return raw
    return canonical(json.loads(serialized)).encode()


def canonical_projection(serialized, fields):
    """Canonicalize the whole document and decode only requested root fields.

    The optional native path validates every byte before returning any field.
    Noncanonical, legacy, nonobject and stdlib-only inputs retain the original
    complete decoder/canonicalizer and its error behavior. No result survives
    this call; the caller still hashes the complete canonical document.
    """
    if (
        type(fields) is not tuple
        or any(type(name) is not str for name in fields)
        or len(set(fields)) != len(fields)
    ):
        raise TypeError("Exact unique string field tuple required")
    if _native is not None and type(serialized) is str:
        try:
            raw = serialized.encode("utf-8")
        except UnicodeEncodeError:
            pass
        else:
            values = _native.project(raw, fields, sys.get_int_max_str_digits())
            if values is not None:
                return raw, {name: json.loads(value) for name, value in values.items()}
    state = json.loads(serialized)
    raw = canonical(state).encode()
    return raw, (
        {name: state[name] for name in fields if name in state} if type(state) is dict else state
    )


def update_object(hasher, fields):
    """Hash a canonical object from independently canonicalized value bytes."""
    hasher.update(b"{")
    for index, name in enumerate(sorted(fields)):
        if index:
            hasher.update(b",")
        hasher.update(canonical(name).encode())
        hasher.update(b":")
        hasher.update(fields[name])
    hasher.update(b"}")
