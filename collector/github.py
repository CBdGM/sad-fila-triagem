"""Cliente mínimo da API REST do GitHub: token, sessão, limites de requisição e paginação."""
import os
import subprocess
import sys
import time
from dataclasses import dataclass

import requests

API = "https://api.github.com"
MAX_RETRIES = 5
MAX_PAGES = 2000


class GitHubError(RuntimeError):
    """Falha ao falar com o GitHub. A mensagem nunca inclui o token."""


class RepoRenamed(GitHubError):
    def __init__(self, old: str, new: str):
        super().__init__(f"{old} agora se chama {new}; atualize o nome em repos.yaml")
        self.old, self.new = old, new


@dataclass
class Usage:
    """Requisições feitas nesta sessão e o limite que o GitHub informou na última resposta."""
    requests: int = 0
    remaining: int | None = None
    limit: int | None = None


def usage(s):
    if not isinstance(getattr(s, "sad_usage", None), Usage):
        s.sad_usage = Usage()
    return s.sad_usage


def _track(s, r):
    u = usage(s)
    u.requests += 1
    if r.headers.get("X-RateLimit-Remaining") is not None:
        u.remaining = int(r.headers["X-RateLimit-Remaining"])
    if r.headers.get("X-RateLimit-Limit") is not None:
        u.limit = int(r.headers["X-RateLimit-Limit"])


def github_token():
    """GITHUB_TOKEN (o Actions fornece) ou, localmente, o token do gh CLI."""
    tok = os.getenv("GITHUB_TOKEN")
    if tok:
        return tok
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                              check=True).stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def session(token=None):
    s = requests.Session()
    s.headers.update({"Accept": "application/vnd.github+json",
                      "X-GitHub-Api-Version": "2022-11-28",
                      "User-Agent": "sad-fila-triagem-collector"})
    tok = token or github_token()
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    else:
        print("AVISO: sem GITHUB_TOKEN nem gh autenticado; limite de 60 requisições/hora.", file=sys.stderr)
    return s


def _wait_seconds(r, now):
    """Quanto esperar se a resposta é de limite de requisição; None se não for."""
    if r.status_code not in (403, 429):
        return None
    retry_after = r.headers.get("Retry-After")
    if retry_after:  # limite secundário
        return max(1, int(retry_after))
    if r.headers.get("X-RateLimit-Remaining") == "0":  # limite primário
        reset = int(r.headers.get("X-RateLimit-Reset", now + 60))
        return max(1, reset - int(now)) + 1
    return None


def get(s, url, params=None, *, sleep=time.sleep, clock=time.time):
    """GET com espera nos limites do GitHub e repetição em erro temporário."""
    return _send(s, "get", url, sleep=sleep, clock=clock, params=params)


def graphql(s, query, variables=None, *, sleep=time.sleep, clock=time.time):
    """Consulta GraphQL. Devolve `data`; itens não encontrados (NOT_FOUND) vêm como nulos.

    Qualquer outro erro na resposta vira GitHubError, com as mensagens do GitHub (sem o token).
    """
    url = f"{API}/graphql"
    for _ in range(MAX_RETRIES):
        body = _send(s, "post", url, sleep=sleep, clock=clock,
                     json={"query": query, "variables": variables or {}}).json()
        errors = body.get("errors") or []
        if any(e.get("type") == "RATE_LIMITED" for e in errors):  # limite do GraphQL vem com 200
            print("Limite do GraphQL atingido; esperando 60s.", file=sys.stderr)
            sleep(60)
            continue
        fatal = [e for e in errors if e.get("type") != "NOT_FOUND"]
        if fatal or body.get("data") is None:
            msgs = "; ".join(e.get("message", "?") for e in (fatal or errors))[:500]
            raise GitHubError(f"consulta GraphQL falhou: {msgs or 'resposta sem dados'}")
        return body["data"]
    raise GitHubError(f"limite do GraphQL não liberou após {MAX_RETRIES} tentativas")


def _send(s, method, url, *, sleep, clock, **kwargs):
    """Requisição com espera nos limites do GitHub e repetição em erro temporário."""
    path = url.replace(API, "")
    for attempt in range(MAX_RETRIES):
        try:
            r = getattr(s, method)(url, timeout=30, **kwargs)
        except requests.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                raise GitHubError(f"erro de rede em {path}: {type(e).__name__}") from None
            sleep(2 ** attempt)
            continue
        _track(s, r)
        wait = _wait_seconds(r, clock())
        if wait is not None:
            print(f"Limite do GitHub atingido; esperando {wait}s.", file=sys.stderr)
            sleep(wait)
            continue
        if r.status_code >= 500:
            if attempt == MAX_RETRIES - 1:
                raise GitHubError(f"GitHub respondeu {r.status_code} em {path} após {MAX_RETRIES} tentativas")
            sleep(2 ** attempt)
            continue
        if r.status_code == 401:
            raise GitHubError("autenticação no GitHub falhou (token inválido ou expirado)")
        if r.status_code == 404:
            raise GitHubError(f"não encontrado no GitHub: {path} (repositório inexistente ou privado?)")
        if r.status_code >= 400:
            raise GitHubError(f"GitHub respondeu {r.status_code} em {path}")
        return r
    raise GitHubError(f"limite do GitHub não liberou após {MAX_RETRIES} tentativas em {path}")


def paginate(s, url, params=None, *, max_pages=MAX_PAGES, on_page=None, **kw):
    """Itens de todas as páginas, seguindo o cabeçalho Link (rel="next").

    on_page(n) é chamado depois de baixar cada página (para mostrar o andamento).
    """
    for n in range(1, max_pages + 1):
        r = get(s, url, params, **kw)
        if on_page:
            on_page(n)
        yield from r.json()
        nxt = r.links.get("next", {}).get("url")
        if not nxt:
            return
        url, params = nxt, None  # a URL do próximo já traz os parâmetros
    raise GitHubError(f"passou de {max_pages} páginas; aumente o teto se for esperado")


def check_repo_name(s, repo, **kw):
    """Falha se o repositório foi renomeado (a busca e as pastas de dados dependem do nome)."""
    current = get(s, f"{API}/repos/{repo}", **kw).json()["full_name"]
    if current.lower() != repo.lower():
        raise RepoRenamed(repo, current)
    return current
