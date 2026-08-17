"""CYRAX persistent Obsidian memory engine with runtime-aware reconciliation."""

from .manager import MemoryManager as _MemoryManager


class RuntimeAwareMemoryManager(_MemoryManager):
    """Memory manager that reconciles explicit runtime facts before retrieval."""

    def _runtime_model(self) -> str | None:
        try:
            from interpreter import interpreter

            configured = str(getattr(getattr(interpreter, "llm", None), "model", ""))
            prefix = "ollama_chat/"
            if configured.startswith(prefix):
                return configured[len(prefix) :].strip() or None
        except Exception:
            return None
        return None

    def reconcile_runtime_model(self) -> list[object]:
        model = self._runtime_model()
        if not model:
            return []
        from .reconciler import reconcile_main_model

        return reconcile_main_model(self, model)

    def semantic_search(self, query: str, limit: int = 5, include_logs: bool = False):
        self.reconcile_runtime_model()
        return super().semantic_search(query, limit=limit, include_logs=include_logs)


MemoryManager = RuntimeAwareMemoryManager

__all__ = ["MemoryManager", "RuntimeAwareMemoryManager"]
