"""Sharded on-disk research vault for authentic billion-record storage experiments.

Each shard is the *real* encrypted desktop Vault, not a simulated counter or
compressed synthetic-pattern generator. Global retrieval preselects up to 256
lexical candidates PER SHARD, then scores those with the existing lexical
encoder to pass up to 256 survivors into the unchanged HingeZero Core/Witness.
This is an approximate distributed shortlist and cannot guarantee full-bank
nearest-neighbour recall. This is research tooling, not the desktop product.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np

from hzdesktop.vault import Vault
from hzdesktop.retrieval import lexical_vector

DEFAULT_SHARD_SIZE = 250_000
MAX_GLOBAL_CANDIDATES = 256


class ShardedVault:
    def __init__(self, directory: str | Path, password: str, *,
                 shard_size: int = DEFAULT_SHARD_SIZE, create: bool):
        if not 1 <= int(shard_size) <= 1_000_000:
            raise ValueError("shard_size must be 1..1,000,000")
        self.directory = Path(directory).expanduser().resolve()
        self.password = password
        self.shard_size = int(shard_size)
        self.active = None
        self.total = 0
        if create:
            if self.directory.exists():
                raise FileExistsError("Refusing to replace a sharded vault directory")
            self.directory.mkdir(parents=True, mode=0o700)
        elif not self.directory.is_dir():
            raise FileNotFoundError("Sharded vault directory does not exist")
        self.paths = sorted(self.directory.glob("shard-*.sqlite3"))
        for index, path in enumerate(self.paths):
            if path.name != f"shard-{index:06d}.sqlite3":
                raise ValueError("Shards must be consecutive with canonical filenames")
            with Vault(path, password) as vault:
                n = vault.count()
                if n < 1 or n > self.shard_size:
                    raise ValueError("Corrupt or unexpected shard record count")
                if index != len(self.paths) - 1 and n != self.shard_size:
                    raise ValueError("Non-terminal shard is not full")
                self.total += n
        if self.paths:
            self.active = Vault(self.paths[-1], password)
        elif create:
            self._new_shard()
        else:
            raise ValueError("No existing shards in directory")

    def _new_shard(self) -> None:
        if self.active is not None:
            self.active.close()
        new_path = self.directory / f"shard-{len(self.paths):06d}.sqlite3"
        self.active = Vault(new_path, self.password, create=True)
        self.paths.append(new_path)

    def add(self, title: str, content: str, source: str) -> str:
        if self.total % self.shard_size == 0 and self.total > 0:
            self._new_shard()
        identifier = self.active.add(title, content, source)
        self.total += 1
        return identifier

    def count(self) -> int:
        return self.total

    def bytes_on_disk(self) -> int:
        return sum(path.stat().st_size for path in self.paths)

    def batch_candidates(self, queries: list[str],
                         limit: int = MAX_GLOBAL_CANDIDATES) -> dict[str, list[dict]]:
        """Search every actual shard, never skip shards; bounded approximate merge.

        The index's per-shard limit makes this an ANN-like shortlist rather
        than an exact global top-k over all one billion source records.
        """
        limit = min(MAX_GLOBAL_CANDIDATES, max(1, int(limit)))
        unique = list(dict.fromkeys(queries))
        qvec = {q: np.asarray(lexical_vector(q), dtype=np.float32) for q in unique}
        winners: dict[str, list[tuple[float, str, dict]]] = {q: [] for q in unique}
        for path in self.paths:
            with Vault(path, self.password) as vault:
                for q in unique:
                    candidates = vault.search_candidates(q, limit=limit)
                    chosen = winners[q]
                    for rec in candidates:
                        lex = np.asarray(lexical_vector(
                            rec.get("title", "") + " " + rec.get("content", "")),
                            dtype=np.float32)
                        score = max(0.0, float(np.dot(qvec[q], lex)))
                        chosen.append((score, str(rec["id"]), rec))
                    chosen.sort(key=lambda x: (-x[0], x[1]))
                    del chosen[limit:]
        return {q: [r for _, _, r in winners[q]] for q in unique}

    def search_candidates(self, query: str, limit: int = 256) -> list[dict]:
        return self.batch_candidates([query], limit=limit)[query]

    def close(self):
        if self.active is not None:
            self.active.close()
            self.active = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
