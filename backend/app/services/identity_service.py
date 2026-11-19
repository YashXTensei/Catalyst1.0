import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class ContributorProfile(BaseModel):
    canonical_name: str
    github_handle: Optional[str] = None
    discourse_handle: Optional[str] = None
    role: str = "contributor"  # "core_maintainer", "author", "contributor"
    aliases: List[str] = []


# Known canonical contributor directory for open-source ecosystems
SEED_CONTRIBUTOR_DIRECTORY: List[ContributorProfile] = [
    ContributorProfile(
        canonical_name="Guido van Rossum",
        github_handle="gvanrossum",
        discourse_handle="guido",
        role="core_maintainer",
        aliases=["guido", "gvanrossum", "Guido", "bdfl"]
    ),
    ContributorProfile(
        canonical_name="Nick Coghlan",
        github_handle="ncoghlan",
        discourse_handle="ncoghlan",
        role="core_maintainer",
        aliases=["ncoghlan", "Nick Coghlan"]
    ),
    ContributorProfile(
        canonical_name="Victor Stinner",
        github_handle="vstinner",
        discourse_handle="vstinner",
        role="core_maintainer",
        aliases=["vstinner", "Victor Stinner"]
    ),
    ContributorProfile(
        canonical_name="Armin Ronacher",
        github_handle="mitsuhiko",
        discourse_handle="mitsuhiko",
        role="core_maintainer",
        aliases=["mitsuhiko", "Armin", "Armin Ronacher"]
    ),
    ContributorProfile(
        canonical_name="Sebastián Ramírez",
        github_handle="tiangolo",
        discourse_handle="tiangolo",
        role="core_maintainer",
        aliases=["tiangolo", "Sebastian Ramirez"]
    ),
]


class IdentityResolutionService:
    """
    Solves Contributor Identity Resolution (Challenge 4.1):
    Resolves contributors across disparate public platforms (GitHub, Discourse, Mailing Lists)
    into unified canonical contributor identities using normalized name matching, handle aliases,
    and platform heuristics.
    """

    def __init__(self):
        self._profiles: Dict[str, ContributorProfile] = {}
        for p in SEED_CONTRIBUTOR_DIRECTORY:
            for alias in p.aliases:
                self._profiles[alias.lower().strip()] = p
            if p.github_handle:
                self._profiles[p.github_handle.lower().strip()] = p
            if p.discourse_handle:
                self._profiles[p.discourse_handle.lower().strip()] = p

    def resolve(self, username: str, platform: str = "github") -> ContributorProfile:
        """Resolves a raw platform username to a canonical ContributorProfile."""
        if not username:
            return ContributorProfile(canonical_name="Unknown Contributor")

        clean = username.strip().lstrip("@").lower()
        if clean in self._profiles:
            return self._profiles[clean]

        # Fuzzy check: replace dots, underscores, dashes
        normalized = re.sub(r"[\._\-]", " ", clean).title()

        new_profile = ContributorProfile(
            canonical_name=normalized,
            github_handle=clean if platform == "github" else None,
            discourse_handle=clean if platform == "discourse" else None,
            role="contributor",
            aliases=[clean, normalized]
        )
        self._profiles[clean] = new_profile
        return new_profile

    def get_cross_platform_identity(self, username: str) -> Dict[str, Any]:
        """Returns unified identity metadata for UI rendering."""
        profile = self.resolve(username)
        return {
            "canonical_name": profile.canonical_name,
            "github": f"@{profile.github_handle}" if profile.github_handle else None,
            "discourse": f"@{profile.discourse_handle}" if profile.discourse_handle else None,
            "role": profile.role,
        }


identity_service = IdentityResolutionService()
