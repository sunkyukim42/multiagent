from __future__ import annotations

from enterprise_decision_agents.ingestion.metadata import RagIngestionError


class CachedApiConnector:
    """Placeholder for future cache-backed API ingestion.

    Task 4 is intentionally local/offline only. This connector exists to make the
    boundary explicit without performing network access.
    """

    def load(self):
        raise RagIngestionError("Cached API ingestion is not enabled in Task 4; use local manifests only.")
