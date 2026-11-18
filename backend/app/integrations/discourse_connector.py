import logging
from typing import List, Dict, Any
import httpx
from app.integrations.base_connector import BaseConnector

logger = logging.getLogger(__name__)


class DiscourseConnector(BaseConnector):
    """
    Extensible connector for Discourse discussion forums (e.g. forum.openzeppelin.com, discourse.llvm.org).
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
                response = await client.get(url, headers={"Accept": "application/json"})
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

                    # Optionally fetch first post content
                    post_content = title
                    try:
                        post_resp = await client.get(f"{base}/t/{topic_id}.json", headers={"Accept": "application/json"})
                        if post_resp.status_code == 200:
                            post_data = post_resp.json()
                            posts = post_data.get("post_stream", {}).get("posts", [])
                            if posts:
                                post_content = posts[0].get("cooked", "") or title
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


discourse_connector = DiscourseConnector()
