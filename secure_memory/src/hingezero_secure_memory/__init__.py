"""HingeZero Secure Memory."""
from .storage import SecureMemory, AccessDenied, IntegrityError, MemoryResult

__all__ = ["SecureMemory", "AccessDenied", "IntegrityError", "MemoryResult"]
__version__ = "0.1.0"
