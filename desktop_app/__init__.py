"""
Namespace package initialiser for the desktop application bundle.

Having this file ensures that `import desktop_app` works even in environments
that do not fully support implicit namespace packages (e.g. older tooling or
watch/reload subprocesses).
"""

__all__ = ["backend", "frontend"]
