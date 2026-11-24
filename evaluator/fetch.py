"""Título e corpo das issues, em lotes pela API GraphQL (issues.jsonl guarda só o hash do corpo)."""
from collector import github


def build_query(numbers):
    aliases = "\n    ".join(f"i{int(n)}: issue(number: {int(n)}) {{ title body }}" for n in numbers)
    return ("query($owner: String!, $name: String!) {\n"
            "  repository(owner: $owner, name: $name) {\n    " + aliases + "\n  }\n}\n")


def fetch_texts(s, repo, numbers, **kw):
    """{número: {"title", "body"}}; issue apagada ou transferida vem como None."""
    owner, name = repo.split("/")
    data = github.graphql(s, build_query(numbers), {"owner": owner, "name": name}, **kw)
    node = data.get("repository")
    if node is None:
        raise github.GitHubError(f"repositório {repo} não encontrado no GraphQL")
    return {n: node.get(f"i{n}") for n in numbers}
