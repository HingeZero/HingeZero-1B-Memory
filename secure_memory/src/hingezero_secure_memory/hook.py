"""Optional host-side event hook. Capture requires an explicit application-controlled opt-in."""
from .storage import SecureMemory


class OptInMemoryHook:
    def __init__(self, vault: SecureMemory, capability: str, *, scope: str = "general", opted_in: bool = False):
        self.vault = vault
        self.capability = capability
        self.scope = scope
        self.opted_in = opted_in

    def on_memory_event(self, *, role: str, kind: str, text: str, source: str):
        if not self.opted_in or role != "user" or kind != "approved_memory":
            return None
        return self.vault.remember_as(self.capability, text, source, scope=self.scope, consent=True)

    def on_user_query(self, query: str):
        return self.vault.recall_as(self.capability, query, scope=self.scope)
