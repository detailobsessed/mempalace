"""Tests for mempalace __init__.py module-level setup."""

import logging


def test_chromadb_telemetry_logger_silenced():
    """Importing mempalace should silence the noisy ChromaDB telemetry logger."""
    import mempalace  # noqa: F401

    logger = logging.getLogger("chromadb.telemetry.product.posthog")
    assert logger.level == logging.CRITICAL
