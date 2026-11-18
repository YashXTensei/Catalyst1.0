from typing import List, Dict, Any
from app.integrations.base_connector import BaseConnector
from app.services.github_service import github_service


class GitHubConnector(BaseConnector):
    @property
    def source_type(self) -> str:
        return "github"

    async def fetch_discussions(self, identifier: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Identifier format: 'owner/repo' or URL.
        """
        owner, repo = github_service.parse_repo_url(identifier)
        return await github_service.fetch_issues_and_prs(owner, repo, page=1, per_page=limit)


github_connector = GitHubConnector()
