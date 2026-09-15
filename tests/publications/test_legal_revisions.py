import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "legal_revisions", Path(__file__).resolve().parents[2] / "tools/legal_gaps/revisions.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_heading_clause_mutation_and_insert():
    before = b"# Contract\n## 1. Price\nUSD 10\n## 2. Term\nThree years\n"
    after = b"# Contract\n## New clause\nNew\n## 1. Price\nUSD 20\n## 2. Term\nThree years\n"
    changes = m.clause_changes(before, after)
    assert len(changes) == 2
    assert any(
        c["heading"] == "Contract / 1. Price" and "-USD 10" in c["diff"] and "+USD 20" in c["diff"]
        for c in changes
    )
    assert not any(c["heading"].endswith("2. Term") for c in changes)


def test_duplicate_headings_preserved():
    assert "A [2]" in m.sections(b"# A\none\n# A\ntwo")


def test_unchanged_draft_is_never_accepted():
    assert m.acceptance(b"unchanged", "draft.pdf") == "DRAFT_NOT_OWNER_ACCEPTED"


def test_receipt_exact_bytes_and_deletion():
    receipt = {"artifacts": {"draft.pdf": m.digest(b"original")}}
    assert m.acceptance(b"original", "draft.pdf", receipt) == "OWNER_RECEIPT_BYTES_MATCH"
    assert m.acceptance(b"changed", "draft.pdf", receipt) == "OWNER_ACCEPTANCE_INVALIDATED_BY_BYTES"
    assert m.acceptance(None, "draft.pdf", receipt) == "OWNER_ACCEPTANCE_INVALIDATED_BY_BYTES"
    assert m.acceptance(b"original", "other.pdf", receipt) == "NOT_COVERED_BY_RECEIPT"


def pdf(texts):
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    for text in texts:
        doc.new_page().insert_text((72, 72), text)
    result = doc.tobytes()
    doc.close()
    return result


def test_pdf_changed_and_deleted_pages(tmp_path):
    pytest.importorskip("PIL")
    result = m.pdf_changes(pdf(["same", "old", "removed"]), pdf(["same", "new"]), tmp_path)
    assert result["before_pages"] == 3 and result["after_pages"] == 2
    assert [(p["page"], p["change"]) for p in result["changed_pages"]] == [
        (2, "modified"),
        (3, "deleted"),
    ]
    assert result["changed_pages"][1]["after"] is None
    assert (tmp_path / "page-002-diff.png").is_file()


def test_pdf_added_page(tmp_path):
    pytest.importorskip("PIL")
    result = m.pdf_changes(pdf(["same"]), pdf(["same", "new"]), tmp_path)
    assert [(p["page"], p["change"]) for p in result["changed_pages"]] == [(2, "added")]


def test_git_baseline_ignores_resealed_manifest(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()

    git("init", "-q")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Test")
    folder = repo / m.PREFIX
    (folder / "source").mkdir(parents=True)
    source = m.PREFIX + "source/test.md"
    structured = m.PREFIX + "source/test.json"
    (repo / source).write_text("# Clause\nOriginal\n")
    (repo / structured).write_text("{}")
    manifest = {
        "packages": [{"source": source, "structured": structured, "artifacts": []}],
        "other_artifacts": [],
    }
    (repo / m.MANIFEST).write_text(json.dumps(manifest))
    git("add", ".")
    git("commit", "-qm", "baseline")
    monkeypatch.setattr(m, "BASELINE", git("rev-parse", "HEAD"))
    (repo / source).write_text("# Clause\nChanged\n")
    manifest["packages"][0]["source_sha256"] = m.digest((repo / source).read_bytes())
    (repo / m.MANIFEST).write_text(json.dumps(manifest))
    report = m.compare(repo, tmp_path / "report")
    row = next(r for r in report["records"] if r["path"] == source)
    assert row["change"] == "modified" and row["acceptance"] == "DRAFT_NOT_OWNER_ACCEPTED"
    assert "Original" in row["clauses"][0]["diff"]
    (repo / source).unlink()
    assert (
        next(r for r in m.compare(repo, tmp_path / "deleted")["records"] if r["path"] == source)[
            "change"
        ]
        == "deleted"
    )


def test_reject_repo_output(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        m.compare(tmp_path, tmp_path / "report")


def test_invalid_receipt_rejected(monkeypatch):
    monkeypatch.setattr(m, "git_bytes", lambda *args: b'{"status":"DRAFT_FOR_REVIEW"}')
    with pytest.raises(ValueError, match="OWNER_ACCEPTED"):
        m.load_receipt(".", "revision", "receipt.json")
