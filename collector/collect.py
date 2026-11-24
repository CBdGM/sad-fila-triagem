"""Coleta de um repositório: primeira execução com tetos ou incremental pelo cursor."""
import calendar
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import github, store

# Versões iniciais dos outros passos; quem muda a pergunta ou a limpeza atualiza no state.json.
DEFAULT_VERSIONS = {"questions": "q1", "cleaning": "clean-1", "calibrator": None, "embeddings": None}


@dataclass
class Changes:
    """O que mudou nesta execução, para os passos seguintes do job."""
    new: list = field(default_factory=list)      # vistas pela primeira vez
    edited: list = field(default_factory=list)   # título ou corpo mudou
    closed: list = field(default_factory=list)   # fecharam (ou já vieram fechadas na primeira vez)

    def as_dict(self):
        return {"new": sorted(self.new), "edited": sorted(self.edited), "closed": sorted(self.closed)}


def utc(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def months_ago(dt, months):
    y, m = dt.year, dt.month - months
    while m <= 0:
        m += 12
        y -= 1
    return dt.replace(year=y, month=m, day=min(dt.day, calendar.monthrange(y, m)[1]))


def body_hash(title, body):
    """SHA-256 de título + corpo crus; não muda com comentários nem labels."""
    return hashlib.sha256(f"{title or ''}\n\n{body or ''}".encode("utf-8")).hexdigest()


def is_pr(item):
    return "pull_request" in item


def to_record(repo, item, first_seen_at):
    """Item da API → linha do contrato issue.schema.json."""
    rec = {
        "schema_version": 1,
        "repo": repo,
        "number": item["number"],
        "url": item["html_url"],
        "title": item["title"] or "",
        "body_sha256": body_hash(item["title"], item.get("body")),
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
        "closed_at": item.get("closed_at"),
        "state": item["state"],
        "state_reason": item.get("state_reason"),
        "labels": [lb["name"] for lb in item.get("labels", [])],
        "first_seen_at": first_seen_at,
    }
    if item.get("author_association"):
        rec["author_association"] = item["author_association"]
    if isinstance(item.get("comments"), int):
        rec["comments"] = item["comments"]
    return rec


class Progress:
    """Mostra o andamento a cada `every` páginas e no fim de cada etapa (emit=None: silencioso)."""

    def __init__(self, emit=None, every=10):
        self.emit, self.every = emit, every
        self.label, self.pages, self.kept, self.total = "", 0, 0, None

    def start(self, label, total=None):
        self.label, self.pages, self.kept, self.total = label, 0, 0, total

    def _msg(self):
        goal = f"/{self.total}" if self.total else ""
        pages = f"{self.pages} página" + ("" if self.pages == 1 else "s")
        return f"{self.label}: {self.kept}{goal} issues, {pages}"

    def page(self, n):
        self.pages = n
        if self.emit and n % self.every == 0:
            self.emit(self._msg())

    def done(self):
        if self.emit:
            self.emit(self._msg() + " (fim)")


def first_run_items(s, repo, open_max, closed_months, now, progress=None, **kw):
    """Abertas mais recentes (até open_max) e fechadas com closed_at na janela."""
    progress = progress or Progress()
    url = f"{github.API}/repos/{repo}/issues"
    progress.start("abertas", open_max)
    for it in github.paginate(s, url, {"state": "open", "sort": "created", "direction": "desc",
                                       "per_page": 100}, on_page=progress.page, **kw):
        if is_pr(it):
            continue
        yield it
        progress.kept += 1
        if progress.kept >= open_max:
            break
    progress.done()
    cutoff = utc(months_ago(now, closed_months))
    progress.start(f"fechadas desde {cutoff[:10]}")
    # since corta por updated_at, que é sempre >= closed_at: nenhuma fechada da janela fica de fora
    for it in github.paginate(s, url, {"state": "closed", "sort": "updated", "direction": "desc",
                                       "since": cutoff, "per_page": 100}, on_page=progress.page, **kw):
        if not is_pr(it) and it.get("closed_at") and it["closed_at"] >= cutoff:
            yield it
            progress.kept += 1
    progress.done()


def incremental_items(s, repo, since, progress=None, **kw):
    progress = progress or Progress()
    url = f"{github.API}/repos/{repo}/issues"
    progress.start(f"atualizadas desde {since}")
    for it in github.paginate(s, url, {"state": "all", "since": since, "sort": "updated",
                                       "direction": "asc", "per_page": 100}, on_page=progress.page, **kw):
        if not is_pr(it):
            yield it
            progress.kept += 1
    progress.done()


def collect_repo(s, repo, cfg, data_dir, *, now=None, done_at=None, progress=None, **kw):
    """Coleta um repositório e grava issues.jsonl e state.json. Devolve Changes.

    Nada é gravado se qualquer passo falhar; o cursor só avança no fim. `now` e `done_at` servem
    para testes; `progress` (Progress) mostra o andamento; `kw` (sleep, clock) vai para o cliente do GitHub.
    """
    github.check_repo_name(s, repo, **kw)
    folder = store.repo_dir(data_dir, repo)
    issues_path, state_path = folder / "issues.jsonl", folder / "state.json"
    state = store.read_state(state_path)
    issues = store.read_issues(issues_path)
    started = now or datetime.now(timezone.utc)
    seen_at = utc(started)

    if state is None or state.get("cursor_since") is None:
        fr = cfg["first_run"]
        items = first_run_items(s, repo, fr["open_max"], fr["closed_months"], started, progress, **kw)
    else:
        items = incremental_items(s, repo, state["cursor_since"], progress, **kw)

    changes = Changes()
    for it in items:
        number = it["number"]
        old = issues.get(number)
        rec = to_record(repo, it, old["first_seen_at"] if old else seen_at)
        if old is None:
            changes.new.append(number)
        elif old["body_sha256"] != rec["body_sha256"]:
            changes.edited.append(number)
        if rec["state"] == "closed" and (old is None or old["state"] != "closed"
                                         or old.get("closed_at") != rec["closed_at"]):
            changes.closed.append(number)
        issues[number] = rec

    store.write_issues(issues_path, issues)
    versions = {**DEFAULT_VERSIONS, **((state or {}).get("versions") or {}), "model": cfg["model"]}
    finished = (done_at or (lambda: datetime.now(timezone.utc)))()
    store.write_state(state_path, {
        "schema_version": 1,
        "repo": repo,
        "cursor_since": seen_at,  # início desta execução: o que mudar durante ela entra na próxima
        "last_success_at": utc(max(finished, started)),
        "versions": {"model": versions["model"], "questions": versions["questions"],
                     "cleaning": versions["cleaning"], "calibrator": versions["calibrator"],
                     "embeddings": versions["embeddings"]},
    })
    return changes
