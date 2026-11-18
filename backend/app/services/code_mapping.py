import re
from typing import List, Set

# Common source file extensions and file paths
FILE_PATH_REGEX = re.compile(
    r"(?:[\w\-\.\/]+\/)?[\w\-\.]+\.(?:py|js|jsx|ts|tsx|go|rs|java|c|cpp|h|hpp|sql|json|yaml|yml|toml|md|sh|proto|rb|php|css|html)",
    re.IGNORECASE
)

# Avoid false positives like "e.g.", "v1.0", "Node.js", "Vue.js", "React.js"
IGNORE_PATTERNS = {
    "node.js", "vue.js", "react.js", "next.js", "e.g.", "i.e.", "etc.", "v1.0", "v2.0",
    "http://", "https://", "github.com", "example.com"
}


class CodeMappingService:
    @staticmethod
    def extract_file_references(text: str, known_files: List[str] = None) -> List[str]:
        """
        Extracts code file paths from discussion text or commit messages.
        Matches regex for valid file patterns and cross-references with known repository/PR files.
        Never invents code references.
        """
        if not text:
            return []

        found: Set[str] = set()

        # 1. Direct matches with known repository files if provided
        if known_files:
            lower_text = text.lower()
            for kf in known_files:
                if kf.lower() in lower_text or kf.split("/")[-1].lower() in lower_text:
                    found.add(kf)

        # 2. Regex matches for code files in the text
        matches = FILE_PATH_REGEX.findall(text)
        for match in matches:
            clean = match.strip("`'\"()[],:; ")
            if len(clean) < 3:
                continue
            if clean.lower() in IGNORE_PATTERNS:
                continue
            if clean.startswith("http") or "/" in clean and clean.split("/")[0] in {"http:", "https:"}:
                continue
            # Ensure it's not a generic word with dot like version 1.0 or domain
            if "." in clean and not clean.endswith("."):
                found.add(clean)

        return sorted(list(found))

    @staticmethod
    def map_decision_to_pr_files(decision_code_refs: List[str], pr_changed_files: List[str]) -> List[str]:
        """Finds overlap between decision code references and PR changed files."""
        if not decision_code_refs or not pr_changed_files:
            return []

        matched = []
        for ref in decision_code_refs:
            ref_clean = ref.lower().lstrip("./")
            for pr_file in pr_changed_files:
                pr_clean = pr_file.lower().lstrip("./")
                if ref_clean == pr_clean or pr_clean.endswith(ref_clean) or ref_clean.endswith(pr_clean):
                    if pr_file not in matched:
                        matched.append(pr_file)
        return matched


code_mapping_service = CodeMappingService()
