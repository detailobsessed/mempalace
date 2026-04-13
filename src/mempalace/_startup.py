"""Module-level side effects: silence noisy loggers.

Imported by __init__.py at package load time.
"""

import logging

# ChromaDB 0.6.x-1.x ships a Posthog telemetry client whose capture() signature
# is incompatible with the bundled posthog library, producing noisy stderr warnings
# on every client operation.  Silence just that logger.
# NOTE: logger path verified against chromadb >=1.5.6.  If a future version
# renames the telemetry module, this becomes a harmless no-op (getLogger on a
# nonexistent name simply creates an unused logger).
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
