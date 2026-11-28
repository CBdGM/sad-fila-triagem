"""Conjunto rotulado (no_action = 1, action = 0) e corte temporal por repositório."""
from dataclasses import dataclass, field

from collector import store

TRAIN_FRACTION = 0.7
INTERNAL = {"OWNER", "MEMBER", "COLLABORATOR"}


@dataclass
class Example:
    repo: str
    number: int
    created_at: str
    text: str
    answers: dict
    y: int
    author_association: str = "NONE"

    @property
    def external(self):
        """Autor de fora da equipe do projeto (quem a fila de triagem atende)."""
        return self.author_association not in INTERNAL


@dataclass
class Split:
    train: list = field(default_factory=list)
    test: list = field(default_factory=list)


def load_repo(data_dir, repo):
    """Exemplos de um repositório: previsões de backfill cujo desfecho atual é no_action ou action."""
    folder = store.repo_dir(data_dir, repo)
    issues = store.read_issues(folder / "issues.jsonl")
    outcome = {}
    for o in store.read_jsonl(folder / "outcomes.jsonl"):  # só acrescenta: a última é a mais recente
        outcome[o["number"]] = o
    seen, out = set(), []
    for p in store.read_jsonl(folder / "predictions.jsonl"):
        n = p["number"]
        if p["mode"] != "backfill" or n in seen or n not in issues or n not in outcome:
            continue
        o, i = outcome[n], issues[n]
        if o["label"] not in ("no_action", "action") or o["closed_at"] != i.get("closed_at"):
            continue  # fora da conta, ou desfecho de um fechamento anterior (issue reaberta)
        if not p.get("input_text"):
            continue
        seen.add(n)
        out.append(Example(repo, n, i["created_at"], p["input_text"], p["answers"], int(o["label"] == "no_action"),
                           i.get("author_association", "NONE")))
    return out


def temporal_split(examples, train_fraction=TRAIN_FRACTION):
    """As mais antigas (por created_at) no treino, as mais recentes no teste."""
    ordered = sorted(examples, key=lambda e: (e.created_at, e.number))
    cut = int(round(len(ordered) * train_fraction))
    return Split(ordered[:cut], ordered[cut:])
