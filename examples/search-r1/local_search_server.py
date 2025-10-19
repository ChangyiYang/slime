"""
Local Search Server for Search-R1

This module provides a local search engine interface that mimics the google_search_server.py API.
It sends requests to a local retrieval server (e.g., running retrieval_server.py from Search-R1)
and formats the results to match the expected output format.

Usage:
    In your generate_with_search.py, replace:
        from google_search_server import google_search
    with:
        from local_search_server import local_search as google_search

    And update SEARCH_R1_CONFIGS:
        SEARCH_R1_CONFIGS = {
            "search_url": "http://127.0.0.1:8000/retrieve",  # URL of local retrieval server
            "topk": 3,
            ...
        }
"""

import asyncio
import argparse
from typing import List, Dict, Optional
import aiohttp


async def local_search(
    search_url: str,
    query: str,
    top_k: int = 5,
    timeout: int = 60,
    proxy: Optional[str] = None,
    snippet_only: bool = False
) -> List[Dict]:
    """
    Call local search engine server and format results to match google_search_server.py output.

    This function provides the same interface as google_search() from google_search_server.py,
    making it a drop-in replacement. The only difference is that instead of using an API key,
    it uses a search_url parameter.

    Args:
        search_url: URL of the local retrieval server (e.g., "http://127.0.0.1:8000/retrieve")
        query: Search query string
        top_k: Number of results to retrieve
        timeout: Request timeout in seconds (default: 60)
        proxy: Proxy URL if needed (not used for local retrieval, kept for API compatibility)
        snippet_only: If True, only return snippet (kept for API compatibility with google_search)

    Returns:
        List of dictionaries with format: [{"document": {"contents": '"<title>"\n<text>'}}]
        This matches the output format of google_search() from google_search_server.py
    """
    # Prepare request payload for local retrieval server
    payload = {
        "queries": [query],
        "topk": top_k,
        "return_scores": False  # We don't need scores for compatibility with google_search_server
    }

    # Send async request to local retrieval server
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    session_kwargs = {}
    # Note: proxy parameter is kept for API compatibility but typically not needed for local server
    if proxy:
        session_kwargs["proxy"] = proxy

    try:
        async with aiohttp.ClientSession(**session_kwargs) as session:
            async with session.post(search_url, json=payload, timeout=timeout_obj) as resp:
                resp.raise_for_status()
                result = await resp.json()
    except Exception as e:
        print(f"Error calling local search engine at {search_url}: {e}")
        return []

    # Parse retrieval results
    # Format from retrieval_server.py: {"result": [[{"id": "...", "contents": "..."}]]}
    retrieval_results = result.get("result", [[]])[0]

    # Format to match google_search_server.py output
    # Google format: [{"document": {"contents": '"<title>"\n<context>'}}]
    contexts = []

    for item in retrieval_results:
        # Extract contents from retrieval result
        # retrieval_server returns: {"id": "...", "contents": '"Title"\nText...'}
        if isinstance(item, dict):
            content = item.get("contents", "")

            if content:
                # Parse title and text
                # The contents from retrieval_server.py are formatted as: '"Title"\nText content...'
                lines = content.split("\n", 1)
                title = lines[0].strip() if lines else "No title."
                text = lines[1].strip() if len(lines) > 1 else ""

                # Ensure title is quoted (remove existing quotes first to avoid double-quoting)
                title = title.strip('"')
                if title:
                    title = f'"{title}"'
                else:
                    title = '"No title."'

                # Ensure we have some content
                if not text:
                    text = "No snippet available."

                # Combine title and text
                formatted_content = f"{title}\n{text}"

                contexts.append({
                    "document": {"contents": formatted_content}
                })
            else:
                # Empty content case - provide default values
                contexts.append({
                    "document": {"contents": '"No title."\nNo snippet available.'}
                })

    # If no results found, return empty list (consistent with google_search_server.py)
    return contexts
