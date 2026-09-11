"""Literature search abstraction: arXiv + OpenAlex clients.

Rules enforced here:
* every returned record carries source provenance (API, URL, retrieval time);
* nothing is invented — empty results return empty lists with the query echoed;
* AI-generated interpretation is never mixed into retrieved metadata.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import httpx

from aimathh.core.logging import get_logger
from aimathh.core.types import Citation

log = get_logger("literature")


class LiteratureClient(ABC):
    name: str = "base"

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> list[Citation]:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, identifier: str) -> dict[str, Any]:
        """Fetch full metadata / abstract by id (arxiv id, DOI, URL)."""
        raise NotImplementedError


class ArxivClient(LiteratureClient):
    name = "arxiv"

    def __init__(self, timeout_s: float = 30.0) -> None:
        self.timeout_s = timeout_s

    async def search(self, query: str, max_results: int = 10) -> list[Citation]:
        url = "https://export.arxiv.org/api/query"
        params = {"search_query": f"all:{query}", "start": 0, "max_results": max_results,
                  "sortBy": "relevance", "sortOrder": "descending"}
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return self._parse(resp.text)

    async def fetch(self, identifier: str) -> dict[str, Any]:
        arxiv_id = identifier.split("/")[-1]
        url = "https://export.arxiv.org/api/query"
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.get(url, params={"id_list": arxiv_id})
            resp.raise_for_status()
            cites = self._parse(resp.text)
        if not cites:
            return {"found": False, "id": identifier}
        c = cites[0]
        return {"found": True, "citation": c.model_dump(), "source": "arxiv"}

    def _parse(self, xml_text: str) -> list[Citation]:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(xml_text)
        out: list[Citation] = []
        for entry in root.findall("a:entry", ns):
            title = (entry.findtext("a:title", "", ns) or "").strip()
            title = re.sub(r"\s+", " ", title)
            authors = [re.sub(r"\s+", " ", (a.findtext("a:name", "", ns) or "").strip())
                       for a in entry.findall("a:author", ns)]
            url = entry.findtext("a:id", "", ns) or ""
            arxiv_id = url.rsplit("/", 1)[-1]
            published = entry.findtext("a:published", "", ns) or ""
            year = int(published[:4]) if published[:4].isdigit() else None
            out.append(Citation(
                title=title, authors=authors, venue="arXiv", year=year,
                arxiv_id=arxiv_id, url=url, retrieved_at=datetime.now(timezone.utc),
                kind="paper_claim", verified_retrieved=True,
            ))
        return out


class OpenAlexClient(LiteratureClient):
    """OpenAlex (Crossref-compatible metadata, no key required)."""

    name = "openalex"

    def __init__(self, timeout_s: float = 30.0, mailto: str = "aimathh@example.org") -> None:
        self.timeout_s = timeout_s
        self.mailto = mailto

    async def search(self, query: str, max_results: int = 10) -> list[Citation]:
        url = "https://api.openalex.org/works"
        params = {"search": query, "per-page": max_results, "mailto": self.mailto}
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.get(url, params=params, headers={"User-Agent": f"aimathh ({self.mailto})"})
            resp.raise_for_status()
            data = resp.json()
        out: list[Citation] = []
        for w in data.get("results", []):
            title = w.get("title") or w.get("display_name") or ""
            authors = [a.get("author", {}).get("display_name", "") for a in w.get("authorships", [])]
            doi = (w.get("doi") or "").replace("https://doi.org/", "")
            venue = ""
            try:
                venue = (w.get("primary_location") or {}).get("source", {}).get("display_name") or ""
            except Exception:
                pass
            out.append(Citation(
                title=title, authors=[a for a in authors if a], venue=venue,
                year=w.get("publication_year"), doi=doi,
                url=w.get("doi") or w.get("id") or "",
                retrieved_at=datetime.now(timezone.utc),
                kind="paper_claim", verified_retrieved=True,
            ))
        return out

    async def fetch(self, identifier: str) -> dict[str, Any]:
        url = f"https://api.openalex.org/works/{identifier}"
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.get(url, params={"mailto": self.mailto})
            if resp.status_code == 404:
                return {"found": False, "id": identifier}
            resp.raise_for_status()
            return {"found": True, "work": resp.json(), "source": "openalex"}


class AggregatingLiteratureClient(LiteratureClient):
    name = "aggregating"

    def __init__(self, clients: list[LiteratureClient] | None = None) -> None:
        self.clients = clients or [ArxivClient(), OpenAlexClient()]

    async def search(self, query: str, max_results: int = 10) -> list[Citation]:
        seen: set[str] = set()
        out: list[Citation] = []
        for client in self.clients:
            try:
                for c in await client.search(query, max_results=max_results):
                    key = (c.doi or c.arxiv_id or c.title).lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(c)
            except Exception as e:  # noqa: BLE001
                log.warning("literature client %s failed: %s", client.name, e)
        return out[:max_results]

    async def fetch(self, identifier: str) -> dict[str, Any]:
        if identifier.startswith("10.") or "doi" in identifier.lower():
            return await OpenAlexClient().fetch(identifier)
        return await ArxivClient().fetch(identifier)


_client: LiteratureClient | None = None


def get_literature_client() -> LiteratureClient:
    global _client
    if _client is None:
        _client = AggregatingLiteratureClient()
    return _client
