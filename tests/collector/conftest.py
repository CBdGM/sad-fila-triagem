"""Sessão falsa do GitHub para testar o coletor sem rede."""
import copy
from urllib.parse import parse_qsl, urlencode, urlsplit

import pytest

API = "https://api.github.com"


class FakeResponse:
    def __init__(self, status=200, body=None, headers=None, next_url=None):
        self.status_code = status
        self._body = body if body is not None else []
        self.headers = headers or {}
        self.links = {"next": {"url": next_url}} if next_url else {}

    def json(self):
        return copy.deepcopy(self._body)


class FakeSession:
    """Responde a partir de uma função (url, params) -> FakeResponse e registra as chamadas."""

    def __init__(self, handler):
        self.handler = handler
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        return self.handler(url, dict(params or {}))


def issue(number, *, state="open", title=None, body="corpo", created="2026-11-01T10:00:00Z",
          updated=None, closed=None, reason=None, labels=(), pr=False, comments=0):
    it = {
        "number": number,
        "html_url": f"https://github.com/o/r/issues/{number}",
        "title": title or f"Issue {number}",
        "body": body,
        "created_at": created,
        "updated_at": updated or created,
        "closed_at": closed,
        "state": state,
        "state_reason": reason,
        "labels": [{"name": n} for n in labels],
        "author_association": "NONE",
        "comments": comments,
    }
    if pr:
        it["pull_request"] = {"url": "x"}
    return it


def paged(items, url, params, page_size=100):
    """Fatia `items` em páginas, com Link next como na API."""
    page = int(params.get("page", 1))
    start = (page - 1) * page_size
    chunk = items[start:start + page_size]
    nxt = None
    if start + page_size < len(items):
        base = urlsplit(url)
        q = dict(parse_qsl(base.query)) | {k: str(v) for k, v in params.items()} | {"page": str(page + 1)}
        nxt = f"{base.scheme}://{base.netloc}{base.path}?{urlencode(q)}"
    return FakeResponse(body=chunk, next_url=nxt)


def params_of(url, params):
    """Parâmetros vindos tanto de params quanto da query da URL (páginas seguintes)."""
    return dict(parse_qsl(urlsplit(url).query)) | {k: str(v) for k, v in params.items()}


@pytest.fixture
def cfg():
    return {"schema_version": 1, "model": "jev-1.14.0",
            "first_run": {"open_max": 2, "closed_months": 1},
            "repos": [{"repo": "o/r", "closing_labels": {"duplicate": "duplicate"}}]}


@pytest.fixture
def nosleep():
    slept = []
    return slept, slept.append
