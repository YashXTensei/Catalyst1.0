from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseConnector(ABC):
    """
    Abstract interface for decision data sources.
    Enables extending DecisionTrail to GitHub, Discourse, Slack, Linear, etc.
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Name of source, e.g. 'github', 'discourse'"""
        pass

    @abstractmethod
    async def fetch_discussions(self, identifier: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetches discussions from this source.
        Returns uniform dicts with:
        source_id, title, body, author, url, discussion_type, created_at_source
        """
        pass
