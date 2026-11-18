import re
import asyncio
import logging
from typing import Tuple, Dict, Any, List, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class GitHubService:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.github_token

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DecisionTrail-App/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @staticmethod
    def parse_repo_url(url: str) -> Tuple[str, str]:
        """
        Parses repository URL or slug into (owner, repo_name).
        Supports:
        - https://github.com/owner/repo
        - http://github.com/owner/repo.git
        - github.com/owner/repo
        - owner/repo
        """
        cleaned = url.strip().rstrip("/")
        if cleaned.endswith(".git"):
            cleaned = cleaned[:-4]

        # Regex for owner/repo
        pattern = r"(?:https?:\/\/)?(?:www\.)?github\.com\/([^\/]+)\/([^\/]+)"
        match = re.search(pattern, cleaned)
        if match:
            return match.group(1), match.group(2)

        # Fallback to slug format "owner/repo"
        parts = cleaned.split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]

        raise ValueError(
            f"Invalid GitHub repository format: '{url}'. Expected format 'owner/repo' or 'https://github.com/owner/repo'"
        )

    async def get_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetches repository metadata from GitHub API."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=self._get_headers())
            if response.status_code == 404:
                raise ValueError(f"Repository '{owner}/{repo}' not found on GitHub or is private.")
            elif response.status_code == 403 or response.status_code == 429:
                reset_time = response.headers.get("x-ratelimit-reset", "soon")
                raise PermissionError(
                    f"GitHub API rate limit exceeded. Please configure GITHUB_TOKEN in backend/.env. (Reset: {reset_time})"
                )
            elif response.status_code != 200:
                raise RuntimeError(f"GitHub API error ({response.status_code}): {response.text}")

            data = response.json()
            return {
                "owner": data.get("owner", {}).get("login", owner),
                "name": data.get("name", repo),
                "full_name": data.get("full_name", f"{owner}/{repo}"),
                "url": data.get("html_url", f"https://github.com/{owner}/{repo}"),
                "description": data.get("description") or "",
                "stars": data.get("stargazers_count", 0),
                "default_branch": data.get("default_branch", "main"),
                "open_issues_count": data.get("open_issues_count", 0),
            }

    async def search_discussions(self, owner: str, repo: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Targeted GitHub search for issues/PRs matching user query keywords in this repository.
        Crucial for the Question-First architecture.
        """
        url = f"{self.BASE_URL}/search/issues"
        per_page = min(limit, 15)

        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = self._get_headers()
            r_issues, r_prs = await asyncio.gather(
                client.get(url, headers=headers, params={"q": f"repo:{owner}/{repo} is:issue {query}", "per_page": per_page, "sort": "relevance"}),
                client.get(url, headers=headers, params={"q": f"repo:{owner}/{repo} is:pr {query}", "per_page": per_page, "sort": "relevance"})
            )

            items = []
            if r_issues.status_code == 200:
                items.extend(r_issues.json().get("items", []))
            if r_prs.status_code == 200:
                items.extend(r_prs.json().get("items", []))

            results = []
            seen_ids = set()
            for item in items:
                sid = str(item.get("id"))
                if sid in seen_ids:
                    continue
                seen_ids.add(sid)
                is_pr = "pull_request" in item
                results.append({
                    "source_id": sid,
                    "number": item.get("number"),
                    "title": item.get("title", ""),
                    "body": item.get("body") or "",
                    "url": item.get("html_url", ""),
                    "author": item.get("user", {}).get("login", ""),
                    "state": item.get("state", "open"),
                    "discussion_type": "pull_request" if is_pr else "issue",
                    "created_at_source": item.get("created_at"),
                })
            return results[:limit]

    async def fetch_issues_and_prs(
        self, owner: str, repo: str, page: int = 1, per_page: int = 20, state: str = "all"
    ) -> List[Dict[str, Any]]:
        """Fetches issues and PRs with pagination."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues"
        params = {"state": state, "sort": "updated", "direction": "desc", "page": page, "per_page": per_page}

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=self._get_headers(), params=params)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch issues/PRs: {response.text}")
                return []

            items = response.json()
            discussions = []
            for item in items:
                is_pr = "pull_request" in item
                discussions.append({
                    "source_id": str(item.get("id")),
                    "number": item.get("number"),
                    "title": item.get("title", ""),
                    "body": item.get("body") or "",
                    "url": item.get("html_url", ""),
                    "author": item.get("user", {}).get("login", ""),
                    "state": item.get("state", "open"),
                    "discussion_type": "pull_request" if is_pr else "issue",
                    "created_at_source": item.get("created_at"),
                })
            return discussions

    async def fetch_pure_issues(
        self, owner: str, repo: str, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Explicitly fetches pure issues (excluding pull requests) via search API.
        Ensures issues are not crowded out in repositories with heavy PR activity.
        """
        url = f"{self.BASE_URL}/search/issues"
        params = {"q": f"repo:{owner}/{repo} is:issue", "sort": "updated", "per_page": min(limit, 50)}

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=self._get_headers(), params=params)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch pure issues: {response.text}")
                return []

            items = response.json().get("items", [])
            issues = []
            for item in items:
                issues.append({
                    "source_id": str(item.get("id")),
                    "number": item.get("number"),
                    "title": item.get("title", ""),
                    "body": item.get("body") or "",
                    "url": item.get("html_url", ""),
                    "author": item.get("user", {}).get("login", ""),
                    "state": item.get("state", "open"),
                    "discussion_type": "issue",
                    "created_at_source": item.get("created_at"),
                })
            return issues

    async def fetch_comments(self, owner: str, repo: str, issue_number: int, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetches comments for an issue or PR to gather rich discussion context."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        params = {"per_page": limit}

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=self._get_headers(), params=params)
            if response.status_code != 200:
                return []

            items = response.json()
            comments = []
            for c in items:
                comments.append({
                    "source_id": str(c.get("id")),
                    "author": c.get("user", {}).get("login", ""),
                    "body": c.get("body") or "",
                    "url": c.get("html_url", ""),
                    "created_at": c.get("created_at"),
                })
            return comments

    async def fetch_pr_details_and_files(
        self, owner: str, repo: str, pr_number: int
    ) -> Dict[str, Any]:
        """Fetches PR metadata, diff stats, and changed files."""
        pr_url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        files_url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/files"

        async with httpx.AsyncClient(timeout=20.0) as client:
            pr_resp = await client.get(pr_url, headers=self._get_headers())
            if pr_resp.status_code == 404:
                raise ValueError(f"Pull Request #{pr_number} not found in {owner}/{repo}.")
            elif pr_resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch PR #{pr_number}: {pr_resp.text}")

            pr_data = pr_resp.json()

            files_resp = await client.get(files_url, headers=self._get_headers())
            changed_files = []
            patches = []
            if files_resp.status_code == 200:
                for f in files_resp.json():
                    filename = f.get("filename")
                    if filename:
                        changed_files.append(filename)
                    patch = f.get("patch")
                    if patch and len(patches) < 5:  # sample first few patches
                        patches.append(f"File {filename}:\n{patch[:600]}")

            return {
                "number": pr_number,
                "title": pr_data.get("title", ""),
                "body": pr_data.get("body") or "",
                "author": pr_data.get("user", {}).get("login", ""),
                "state": pr_data.get("state", "open"),
                "url": pr_data.get("html_url", ""),
                "changed_files": changed_files,
                "patches_sample": "\n\n".join(patches),
                "additions": pr_data.get("additions", 0),
                "deletions": pr_data.get("deletions", 0),
            }


github_service = GitHubService()
