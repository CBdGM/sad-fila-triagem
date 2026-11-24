"""Limpeza do texto da issue: camada 1 (regex) do clean.py da PoC (sad-poc-decisao), sem mudanças.

Tira pistas de formato que entregariam a resposta (templates, comandos de bot) e encurta blocos de
código longos. Mudar qualquer regra exige subir CLEANING_VERSION."""
import re

CLEANING_VERSION = "clean-1"
CODE_KEEP_LINES = 10


HTML_COMMENT = re.compile(r"<!--.*?(-->|$)", re.S)
HTML_TAGS = re.compile(r"</?(details|summary|br|p|sub|sup|b|i|kbd)\b[^>]*>", re.I)
# Comandos do Prow/bots que entregam o rótulo (/kind bug, /sig node, /priority ...).
BOT_LINE = re.compile(
    r"^[ \t>]*/(kind|priority|sig|triage|area|wg|remove-[\w-]+|label|assign|unassign|cc|uncc|"
    r"lifecycle|milestone|close|reopen|retitle|hold|good-first-issue|help|ok-to-test|lgtm|approve)"
    r"\b.*$", re.M | re.I)
BOT_INLINE = re.compile(r"(?<!\S)/(kind|priority|sig|triage|area|wg)\s+[\w/-]+", re.I)
# Cabeçalhos de template (bug, feature, support, docs). Também entregam o rótulo.
TEMPLATE_HEADING = re.compile(
    r"^#{1,6}\s*(what happened\??|what did you expect to happen\??|"
    r"how can we reproduce it.*|anything else we need to know\??|kubernetes version|"
    r"cloud provider|os version|install tools|container runtime.*|related plugins.*|"
    r"what would you like to be added\??|why is this needed\??|"
    r"which jobs are (failing|flaking).*|which tests? (are|is) (failing|flaking).*|"
    r"since when has it been (failing|flaking).*|testgrid link|reason for failure.*|"
    r"(bug|feature|enhancement)( request| report)?|describe the (bug|feature).*|"
    r"expected behavio(u)?r|actual behavio(u)?r|steps to reproduce)\s*:?\s*$", re.M | re.I)
# Seções de formulário que existem só num dos templates (em geral, ambiente/versões no de bug).
# Saem inteiras, com título e conteúdo: numa auditoria do Kubernetes, "kubectl version" aparecia em
# 46% dos bugs e 2% dos não bugs; no Airflow, versão/Deployment/Helm só existem no template de bug.
TEMPLATE_DROP_SECTION = re.compile(
    r"^#{1,6}\s*("
    # Kubernetes
    r"kubernetes version|cloud provider|os version|install tools|container runtime[^\n]*|"
    r"related plugins[^\n]*|"
    # Apache Airflow
    r"under which category[^\n]*|apache airflow version|operating system|deployment( details)?|"
    r"apache airflow provider[^\n]*|versions of apache airflow providers|official helm chart version|"
    r"helm chart configuration|docker image customizations|are you willing to submit[^\n]*|"
    r"code of conduct|related issues"
    r")\s*:?\s*$.*?(?=^#{1,6}\s|\Z)", re.M | re.S | re.I)
# Qualquer outro cabeçalho Markdown sai inteiro (só o conteúdo abaixo fica): títulos de template
# como "Use case/motivation" ou "What happened?" diriam a classe mesmo sem o "#".
OTHER_HEADING = re.compile(r"^#{1,6}[ \t]+.*$", re.M)
CHECKBOX = re.compile(r"^\s*[-*]\s*\[[ xX]\].*$", re.M)
NO_RESPONSE = re.compile(r"^\s*_No response_\s*$", re.M)
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)|<img\b[^>]*>", re.I)
CODE_BLOCK = re.compile(r"(```|~~~)[^\n]*\n(.*?)(\n\1|\Z)", re.S)
TITLE_PREFIX = re.compile(
    r"^\s*[\[(]?\s*(bug|feature( request)?|enhancement|question|support|docs?|"
    r"documentation|regression|failing test|flaky test|flake)\s*[\])]?\s*[:\-]?\s+", re.I)


def _shorten_code(m):
    lines = m.group(2).split("\n")
    if len(lines) <= CODE_KEEP_LINES:
        return "```\n" + m.group(2) + "\n```"
    kept = "\n".join(lines[:CODE_KEEP_LINES])
    return f"```\n{kept}\n[... {len(lines) - CODE_KEEP_LINES} more lines]\n```"


def clean_body(body: str) -> str:
    t = (body or "").replace("\r\n", "\n")
    t = HTML_COMMENT.sub("", t)
    # Tira os blocos de código do caminho (placeholders) para que as regras abaixo
    # não mexam no conteúdo deles (ex.: um "# comentário" não é cabeçalho).
    blocks = []

    def stash(m):
        blocks.append(_shorten_code(m))
        return f"\x00{len(blocks) - 1}\x00"

    t = CODE_BLOCK.sub(stash, t)
    t = BOT_LINE.sub("", t)
    t = BOT_INLINE.sub("", t)
    t = TEMPLATE_DROP_SECTION.sub("", t)  # depois do stash: um "# comentário" no código não corta a seção
    t = TEMPLATE_HEADING.sub("", t)
    t = OTHER_HEADING.sub("", t)
    t = CHECKBOX.sub("", t)
    t = NO_RESPONSE.sub("", t)
    t = HTML_TAGS.sub("", t)
    t = IMAGE.sub("[image]", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"(?<=\S)[ \t]{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"\x00(\d+)\x00", lambda m: blocks[int(m.group(1))], t)
    return t.strip()


def clean_title(title: str) -> str:
    return TITLE_PREFIX.sub("", title or "").strip()


def clean_issue(issue: dict) -> str:
    """Texto limpo: título + linha em branco + corpo limpo."""
    body = clean_body(issue.get("body", ""))
    title = clean_title(issue.get("title", ""))
    return f"{title}\n\n{body}" if body else title
