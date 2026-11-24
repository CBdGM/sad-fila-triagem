"""GitHub e Jev simulados para testar o avaliador sem rede."""
from collector import store
from collector.collect import to_record

from ..collector.conftest import FakeResponse, issue

MODEL = "jev-1.14.0"


def jev_answers(p=0.9):
    return {"is_defect": {"type": "noul", "noul": p}, "actionable": {"type": "noul", "noul": 0.8},
            "enough_info": {"type": "noul", "noul": 0.7}, "usage_question": {"type": "noul", "noul": 0.1},
            "severity": {"type": "score", "probabilities": {"0": 0.1, "1": 0.2, "2": 0.6, "3": 0.1}, "score": 1.7}}


class JevSession:
    """Responde como o /v1/systemone; `responses` sobrescreve (status, body, headers) por chamada."""

    def __init__(self, responses=None, served_by=MODEL, fail_on_call=None):
        self.responses, self.served_by, self.fail_on_call = list(responses or []), served_by, fail_on_call
        self.calls = []
        self.headers = {}

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, json))
        if self.fail_on_call == len(self.calls):
            r = FakeResponse(400, body={"error": "bad"})
            r.text = '{"error": "bad"}'
            return r
        if self.responses:
            status, body, headers = self.responses.pop(0)
            return FakeResponse(status, body=body, headers=headers)
        return FakeResponse(200, body={"model": self.served_by, "answers": jev_answers(),
                                       "usage": {"input_tokens": 300, "output_tokens": 20}},
                            headers={"x-typesafe-request-id": f"req_{len(self.calls)}"})


class GitHubSession:
    """Responde ao GraphQL com título e corpo; `texts` = {número: (título, corpo)}; ausente = nula."""

    def __init__(self, texts):
        self.texts, self.calls, self.headers = texts, 0, {}

    def post(self, url, json=None, timeout=None):
        self.calls += 1
        nums = [int(line.split(":")[0].strip()[1:]) for line in json["query"].splitlines()
                if line.strip().startswith("i") and "issue(number" in line]
        repo = {f"i{n}": ({"title": self.texts[n][0], "body": self.texts[n][1]} if n in self.texts else None)
                for n in nums}
        return FakeResponse(body={"data": {"repository": repo}})


def rec(n, *, state="open", title=None, body="corpo", created=None, closed=None):
    created = created or f"2026-11-{n:02d}T00:00:00Z"
    return to_record("o/r", issue(n, state=state, title=title, body=body, created=created, closed=closed,
                                  reason="completed" if state == "closed" else None),
                     "2026-11-20T00:00:00Z")


def outcome(n, label, closed):
    return {"schema_version": 1, "repo": "o/r", "number": n, "recorded_at": "2026-11-21T00:00:00Z",
            "closed_at": closed, "state_reason": "completed", "labels_at_close": [], "closed_by": "dev",
            "closed_by_bot": False, "merged_pr": 1 if label == "action" else None, "label": label,
            "reason": "other" if label == "no_action" else None,
            "exclusion_reason": "completed_without_pr" if label == "excluded" else None, "rules_version": "gab-1"}


def write(tmp_path, records, outcomes=()):
    folder = tmp_path / "o__r"
    store.write_issues(folder / "issues.jsonl", {r["number"]: r for r in records})
    if outcomes:
        store.append_jsonl(folder / "outcomes.jsonl", list(outcomes), "outcome")
    return folder


def texts_of(records):
    return {r["number"]: (r["title"], "corpo") for r in records}
