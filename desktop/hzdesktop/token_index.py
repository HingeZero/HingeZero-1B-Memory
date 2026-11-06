"""Keyed lexical candidate index for an encrypted local HingeZero vault.

This is *candidate retrieval*, not HingeZero refinement or a billion-record
performance result. The original HingeZero Core/Witness still reranks and checks
the bounded candidate bank. HMAC hides plaintext terms, but search/access
patterns and token frequencies still leak to an attacker who obtains the DB.
"""
from __future__ import annotations

import hashlib
import hmac

from .retrieval import tokens

MAX_QUERY_TERMS = 32


def terms(text: str) -> list[str]:
    return sorted(set(tokens(text)))


def key_for_term(secret: bytes, term: str) -> bytes:
    return hmac.new(secret, b"HZMemory-token-index-v1\x00" + term.encode("utf-8"),
                    hashlib.sha256).digest()[:16]
