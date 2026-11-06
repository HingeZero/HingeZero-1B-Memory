"""Scalable encrypted candidate-index regression checks (NOT a 1B benchmark)."""
import sqlite3

from hzdesktop.retrieval import search
from hzdesktop.vault import BROWSE_PAGE_SIZE, MAX_RECORDS, Vault


PASSWORD = "long-enough-test-passphrase"


def test_indexed_candidate_recall_witness_and_delete(tmp_path):
    path = tmp_path / "vault.sqlite"
    with Vault(path, PASSWORD, create=True) as vault:
        target = vault.add("HingeZero design", "HingeZero remembers transformer milestones")
        vault.add("Groceries", "Milk and orange juice")
        rows = vault.search_candidates("transformer milestones")
        assert [r["id"] for r in rows] == [target]
        matched = search(rows, "transformer milestones")
        assert matched[0]["record"]["id"] == target
        assert matched[0]["witness_verified"] is True
        assert b"transformer" not in path.read_bytes()
        assert b"milestones" not in path.read_bytes()
        vault.delete(target)
        assert vault.search_candidates("transformer") == []
        assert vault.count() == 1
    with Vault(path, PASSWORD) as vault:
        assert vault.search_candidates("orange juice")[0]["title"] == "Groceries"


def test_old_v1_database_is_indexed_on_unlock(tmp_path):
    path = tmp_path / "vault.sqlite"
    with Vault(path, PASSWORD, create=True) as vault:
        identifier = vault.add("Legacy meeting", "Remember the telescope appointment")
    # Simulate a pre-index v1 database, leaving the encrypted records untouched.
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE term_index")
        db.execute("DELETE FROM meta WHERE key = 'token_index_v1'")
    with Vault(path, PASSWORD) as vault:
        assert vault.search_candidates("telescope")[0]["id"] == identifier
        assert vault.count() == 1


def test_paging_and_billion_ceiling_are_not_billion_benchmark(tmp_path):
    assert MAX_RECORDS == 1_000_000_000
    with Vault(tmp_path / "vault.sqlite", PASSWORD, create=True) as vault:
        for i in range(BROWSE_PAGE_SIZE + 3):
            vault.add(f"Page {i}", f"memory entry {i}")
        newest, next_cursor = vault.list_recent()
        assert len(newest) == BROWSE_PAGE_SIZE
        assert newest[0]["title"] == f"Page {BROWSE_PAGE_SIZE + 2}"
        assert next_cursor is not None
        older, final_cursor = vault.list_recent(before_rowid=next_cursor)
        assert len(older) == 3
        assert final_cursor is None
        assert vault.count() == BROWSE_PAGE_SIZE + 3
