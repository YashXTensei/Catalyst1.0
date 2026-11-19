import re
import html
import logging
from typing import List, Dict, Any, Optional
import httpx
from app.integrations.base_connector import BaseConnector

logger = logging.getLogger(__name__)


def clean_html(raw_html: str) -> str:
    """Converts HTML post body into clean plain text."""
    if not raw_html:
        return ""
    # Replace <br> and </p> with newlines
    text = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Collapse excess whitespace while keeping paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


class DiscourseConnector(BaseConnector):
    """
    Extensible connector for Discourse discussion forums (e.g. discuss.python.org, forum.openzeppelin.com).
    Fetches latest topics and decision discussions via public Discourse REST API.
    """

    @property
    def source_type(self) -> str:
        return "discourse"

    async def fetch_discussions(self, forum_base_url: str, limit: int = 20) -> List[Dict[str, Any]]:
        base = forum_base_url.rstrip("/")
        url = f"{base}/latest.json"

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(url, headers={"Accept": "application/json", "User-Agent": "DecisionTrail/1.0"})
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch from Discourse forum {base}: {response.status_code}")
                    return []

                data = response.json()
                topics = data.get("topic_list", {}).get("topics", [])
                results = []

                for t in topics[:limit]:
                    topic_id = t.get("id")
                    title = t.get("title", "")
                    slug = t.get("slug", "")
                    topic_url = f"{base}/t/{slug}/{topic_id}"

                    post_content = title
                    try:
                        post_resp = await client.get(
                            f"{base}/t/{topic_id}.json",
                            headers={"Accept": "application/json", "User-Agent": "DecisionTrail/1.0"}
                        )
                        if post_resp.status_code == 200:
                            post_data = post_resp.json()
                            posts = post_data.get("post_stream", {}).get("posts", [])
                            if posts:
                                post_content = clean_html(posts[0].get("cooked", "")) or title
                    except Exception:
                        pass

                    results.append({
                        "source_id": f"discourse_{topic_id}",
                        "title": title,
                        "body": post_content,
                        "author": t.get("last_poster_username", "discourse_user"),
                        "url": topic_url,
                        "discussion_type": "discourse_topic",
                        "created_at_source": t.get("created_at"),
                    })

                return results
            except Exception as e:
                logger.error(f"Error querying Discourse {base}: {e}")
                return []

    async def fetch_topic_by_url(self, topic_url: str, max_posts: int = 15) -> Optional[Dict[str, Any]]:
        """
        Fetches full discussion details for a specific Discourse topic URL.
        Extracts the initial proposal post and key discussion replies.
        """
        match = re.search(r"(https?://[^/]+)/t/(?:[a-zA-Z0-9\-_]+/)?(\d+)", topic_url)
        if not match:
            logger.warning(f"Invalid Discourse URL format: {topic_url}")
            return None

        base_host = match.group(1)
        topic_id = match.group(2)
        endpoint = f"{base_host}/t/{topic_id}.json"

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.get(
                    endpoint,
                    headers={"Accept": "application/json", "User-Agent": "DecisionTrail-PEPBenchmark/1.0"}
                )
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch Discourse topic {endpoint}: HTTP {response.status_code}")
                    return None

                data = response.json()
                title = data.get("title", f"Topic {topic_id}")
                posts = data.get("post_stream", {}).get("posts", [])
                if not posts:
                    return None

                # First post is the original PEP proposal or topic introduction
                first_post = posts[0]
                first_body = clean_html(first_post.get("cooked", ""))
                first_author = first_post.get("username", "author")

                comments = []
                participants = set([first_author])

                # Process subsequent replies up to max_posts
                for p in posts[1:max_posts]:
                    cooked = p.get("cooked", "")
                    clean_text = clean_html(cooked)
                    author = p.get("username", "participant")
                    participants.add(author)
                    post_num = p.get("post_number", 1)
                    post_url = f"{base_host}/t/{topic_id}/{post_num}"

                    comments.append({
                        "author": author,
                        "body": clean_text[:1200],  # Bound length for context management
                        "post_number": post_num,
                        "url": post_url,
                    })

                return {
                    "topic_id": topic_id,
                    "title": title,
                    "body": first_body[:3000],  # Bound first post length
                    "author": first_author,
                    "url": topic_url,
                    "posts_count": data.get("posts_count", len(posts)),
                    "participants": list(participants),
                    "comments": comments,
                }
            except Exception as e:
                logger.error(f"Error fetching topic {topic_url}: {e}")
                return None


discourse_connector = DiscourseConnector()
