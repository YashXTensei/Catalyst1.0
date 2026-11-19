import re
import logging
from typing import Dict, Any, List, Optional, Tuple
import httpx

logger = logging.getLogger(__name__)

# Base URLs for official Python PEPs
PEP_RAW_BASE = "https://raw.githubusercontent.com/python/peps/main/peps"
PEP_WEB_BASE = "https://peps.python.org"

# Curated benchmark candidate PEPs with confirmed discuss.python.org threads & rejected ideas
VERIFIED_CANDIDATE_PEPS = [695, 654, 703, 692]


class PEPDatasetService:
    """
    Service responsible for fetching and parsing official Python PEP documents from python/peps.
    Extracts ground-truth 'Rejected Ideas' and official discussion links while maintaining
    strict isolation from the AI extraction pipeline.
    """

    @staticmethod
    async def fetch_pep_raw(pep_number: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Fetches the raw PEP document from GitHub python/peps repository (supports .rst and .md).
        Returns (content, file_extension) or (None, None) if not found.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            for ext in ["rst", "md"]:
                url = f"{PEP_RAW_BASE}/pep-{pep_number:04d}.{ext}"
                try:
                    resp = await client.get(url, headers={"User-Agent": "DecisionTrail-PEPBenchmark/1.0"})
                    if resp.status_code == 200:
                        return resp.text, ext
                except Exception as e:
                    logger.debug(f"Failed to fetch {url}: {e}")
        return None, None

    @staticmethod
    def parse_pep_metadata(content: str, pep_number: int) -> Dict[str, Any]:
        """
        Parses RFC 822 / YAML style metadata headers from the PEP header block.
        """
        title_m = re.search(r"^Title:\s*(.+)$", content, re.MULTILINE)
        status_m = re.search(r"^Status:\s*(.+)$", content, re.MULTILINE)
        author_m = re.search(r"^Author:\s*(.+)$", content, re.MULTILINE)

        title = title_m.group(1).strip() if title_m else f"PEP {pep_number}"
        status = status_m.group(1).strip() if status_m else "Unknown"
        author = author_m.group(1).strip() if author_m else "Python Core"

        # Find discuss.python.org URLs anywhere in headers or text
        discuss_links = list(dict.fromkeys(
            re.findall(r"https://discuss\.python\.org/t/[a-zA-Z0-9\-_/]+", content)
        ))

        # Filter to base topic URLs (remove post suffixes like /92)
        base_discuss_urls = []
        for link in discuss_links:
            # Clean trailing punctuation
            clean_link = link.rstrip("/.)>,;\"'")
            # Match base topic pattern: https://discuss.python.org/t/{slug}/{id} or /t/{id}
            m = re.match(r"(https://discuss\.python\.org/t/(?:[a-zA-Z0-9\-_]+/)?\d+)", clean_link)
            if m:
                base_url = m.group(1)
                if base_url not in base_discuss_urls:
                    base_discuss_urls.append(base_url)

        return {
            "pep_number": pep_number,
            "title": title,
            "status": status,
            "author": author,
            "official_url": f"{PEP_WEB_BASE}/pep-{pep_number:04d}/",
            "discuss_urls": base_discuss_urls,
            "primary_discussion_url": base_discuss_urls[0] if base_discuss_urls else None,
        }

    @staticmethod
    def parse_rejected_ideas(content: str) -> List[Dict[str, str]]:
        """
        Extracts ground-truth rejected ideas and reasoning from the 'Rejected Ideas'
        or 'Rejected Alternatives' section of the PEP.
        Returns a list of dicts: [{"idea": title, "reason": rationale}].
        """
        # Match Rejected section heading (RST style: underline with =, -, or ~)
        rej_match = re.search(
            r"\n(Rejected Ideas|Rejected Alternatives|Rejected alternative proposals)\s*\n([=\-]+)",
            content,
            re.IGNORECASE,
        )
        if not rej_match:
            # Try Markdown style (## Rejected Ideas)
            rej_md = re.search(
                r"\n(##?\s+(?:Rejected Ideas|Rejected Alternatives))\s*\n",
                content,
                re.IGNORECASE,
            )
            if not rej_md:
                return []
            start_pos = rej_md.end()
            # Next top-level heading starts next section
            next_sec = re.search(r"\n##?\s+[^\n]+", content[start_pos:])
            sec_content = content[start_pos : start_pos + next_sec.start()] if next_sec else content[start_pos:]
            # Subsections in Markdown (### Idea)
            sub_matches = list(re.finditer(r"\n###\s+([^\n]+)", sec_content))
            ideas = []
            for i, sm in enumerate(sub_matches):
                title = sm.group(1).strip()
                b_start = sm.end()
                b_end = sub_matches[i + 1].start() if i + 1 < len(sub_matches) else len(sec_content)
                body = sec_content[b_start:b_end].strip()
                ideas.append({"idea": title, "reason": body})
            return ideas

        section_underline = rej_match.group(2)
        start_pos = rej_match.end()

        # Major section boundary: same character underline of length >= 3
        major_char = re.escape(section_underline[0])
        next_sec_pattern = re.compile(rf"\n([^\n]+)\n{major_char}{{3,}}\n")
        next_match = next_sec_pattern.search(content[start_pos:])
        sec_content = content[start_pos : start_pos + next_match.start()] if next_match else content[start_pos:]

        # Subsections inside section are underlined with a different character or '-'
        sub_pattern = re.compile(r"\n([^\n]+)\n([\-\~`]{3,})\n")
        sub_matches = list(sub_pattern.finditer(sec_content))

        ideas = []
        if sub_matches:
            for i, sm in enumerate(sub_matches):
                title = sm.group(1).strip()
                body_start = sm.end()
                body_end = sub_matches[i + 1].start() if i + 1 < len(sub_matches) else len(sec_content)
                body = sec_content[body_start:body_end].strip()
                # Clean RST directives (::, .. code::)
                clean_body = re.sub(r"::|\.\.[^\n]*\n", "", body).strip()
                # Remove extra blank lines
                clean_body = re.sub(r"\n\s*\n", "\n\n", clean_body)
                ideas.append({"idea": title, "reason": clean_body})
        else:
            # Bullet point fallback
            bullets = re.split(r"\n\s*[\*\-]\s+", sec_content)
            for b in bullets[1:]:
                clean_b = b.strip()
                if not clean_b or clean_b == "<TBD>":
                    continue
                parts = clean_b.split(":", 1)
                title = parts[0].strip().strip("*`_")
                reason = parts[1].strip() if len(parts) > 1 else clean_b
                ideas.append({"idea": title, "reason": reason})

        # Filter out placeholders like <TBD>
        valid_ideas = [item for item in ideas if item["idea"].strip() and item["idea"].strip() != "<TBD>"]
        return valid_ideas

    @classmethod
    async def get_pep_ground_truth(cls, pep_number: int) -> Optional[Dict[str, Any]]:
        """
        Fetches and extracts full ground truth for a PEP.
        Keeps ground truth completely isolated for evaluation only.
        """
        content, ext = await cls.fetch_pep_raw(pep_number)
        if not content:
            logger.warning(f"PEP {pep_number} could not be fetched from {PEP_RAW_BASE}")
            return None

        metadata = cls.parse_pep_metadata(content, pep_number)
        rejected_ideas = cls.parse_rejected_ideas(content)

        return {
            **metadata,
            "format": ext,
            "rejected_ideas": rejected_ideas,
            "total_ground_truth_rejected": len(rejected_ideas),
            "raw_length": len(content),
        }

    @staticmethod
    def list_candidate_peps() -> List[int]:
        """Returns the verified candidate PEP list."""
        return list(VERIFIED_CANDIDATE_PEPS)


pep_dataset_service = PEPDatasetService()
