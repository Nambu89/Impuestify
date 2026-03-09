"""
robots.txt checker — respects site crawling rules.
"""
import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from .config import USER_AGENT

logger = logging.getLogger(__name__)

_cache: dict[str, RobotFileParser | None] = {}


def _get_robots_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


def can_fetch(url: str) -> bool:
    """Check if URL is allowed by robots.txt. Returns True if allowed or if robots.txt is unavailable."""
    parsed = urlparse(url)
    domain = parsed.netloc

    if domain not in _cache:
        robots_url = _get_robots_url(url)
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
            _cache[domain] = rp
            logger.debug(f"Loaded robots.txt for {domain}")
        except Exception:
            # If robots.txt is unavailable, allow fetching (fail open)
            logger.debug(f"No robots.txt for {domain}, allowing all")
            _cache[domain] = None

    rp = _cache[domain]
    if rp is None:
        return True

    allowed = rp.can_fetch(USER_AGENT, url)
    if not allowed:
        logger.warning(f"robots.txt BLOCKS: {url}")
    return allowed


def clear_cache() -> None:
    """Clear the robots.txt cache (for testing)."""
    _cache.clear()
