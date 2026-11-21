"""Fatos de fechamento vindos do GitHub, em lotes pela API GraphQL."""
from collector import github

EVENTS_PER_ISSUE = 50

FRAGMENT = """
fragment Closing on Issue {
  number
  timelineItems(last: %d, itemTypes: [CLOSED_EVENT, CROSS_REFERENCED_EVENT]) {
    nodes {
      __typename
      ... on ClosedEvent {
        actor { __typename login }
        closer { __typename ... on PullRequest { number merged repository { nameWithOwner } } }
      }
      ... on CrossReferencedEvent {
        source { __typename ... on PullRequest { number merged repository { nameWithOwner } } }
      }
    }
  }
}
""" % EVENTS_PER_ISSUE


def build_query(numbers):
    """Uma consulta com um alias por issue (i<número>)."""
    aliases = "\n    ".join(f"i{n}: issue(number: {int(n)}) {{ ...Closing }}" for n in numbers)
    return ("query($owner: String!, $name: String!) {\n"
            "  repository(owner: $owner, name: $name) {\n    " + aliases + "\n  }\n}\n" + FRAGMENT)


def normalize_actor(actor):
    """(login, é_bot). Login de bot no formato da API REST e do repos.yaml: termina em [bot]."""
    if not actor or not actor.get("login"):
        return None, False
    login = actor["login"]
    is_bot = actor.get("__typename") == "Bot" or login.endswith("[bot]")
    if is_bot and not login.endswith("[bot]"):
        login += "[bot]"
    return login, is_bot


def _merged_pr_of(node, repo):
    """Número do PR se o nó é PR mesclado do mesmo repositório; senão None."""
    if (node and node.get("__typename") == "PullRequest" and node.get("merged")
            and (node.get("repository") or {}).get("nameWithOwner", "").lower() == repo.lower()):
        return node["number"]
    return None


def extract(repo, issue_node):
    """Fatos de uma issue: quem fechou, se é bot, PR mesclado ligado e se os eventos vieram cortados."""
    events = (issue_node.get("timelineItems") or {}).get("nodes") or []
    closed = [e for e in events if e.get("__typename") == "ClosedEvent"]
    last_close = closed[-1] if closed else None
    closed_by, is_bot = normalize_actor(last_close.get("actor") if last_close else None)

    merged_pr = _merged_pr_of(last_close.get("closer") if last_close else None, repo)
    if merged_pr is None:
        merged_pr = next((n for n in (_merged_pr_of(e.get("source"), repo) for e in events
                                      if e.get("__typename") == "CrossReferencedEvent") if n), None)
    return {"closed_by": closed_by, "closed_by_bot": is_bot, "merged_pr": merged_pr,
            "truncated": len(events) >= EVENTS_PER_ISSUE}


def fetch_batch(s, repo, numbers, **kw):
    """{número: fatos} para um lote; issue apagada ou transferida vem como None."""
    owner, name = repo.split("/")
    data = github.graphql(s, build_query(numbers), {"owner": owner, "name": name}, **kw)
    repo_node = data.get("repository")
    if repo_node is None:
        raise github.GitHubError(f"repositório {repo} não encontrado no GraphQL")
    return {n: (extract(repo, repo_node[f"i{n}"]) if repo_node.get(f"i{n}") else None) for n in numbers}
