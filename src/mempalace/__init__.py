"""MemPalace — Give your AI a memory. No API key required."""

__version__ = "0.1.1"

from . import _startup as _startup  # side-effects: silence loggers, platform workarounds
from .cli import main

__all__ = ["__version__", "main"]
