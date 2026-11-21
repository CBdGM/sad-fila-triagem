## Context

Ver `proposal.md` (Why). Os formatos de saída já estão fixados em `contracts/` (`issue.schema.json`, `state.schema.json`, `repos.schema.json`). Medição feita em 21/11/2026 no `apache/airflow`:

| Medida | Valor |
|---|---|
| Issues fechadas nos últimos 6 meses (busca) | 1.283 |
| PRs fechados no mesmo período | 8.010 |
| Issues numa página de 100 itens da lista `/issues` (fechados desde 01/11) | 7 (o resto é PR) |
| Limite da API com token pessoal | 5.000 requisições/hora (`core`) |

A lista `/issues` traz `state_reason`, `labels`, `author_association`, `comments` e `closed_by` sem chamada extra.

## Goals / Non-Goals

**Goals:**
- Coletor simples, testável sem rede, que rode igual na máquina de alguém e no Actions.
- Saída pronta para o Back fazer a Fase 0 (issues fechadas de 6 meses com `state_reason` e labels).

**Non-Goals:**
- Desfechos (`outcomes.jsonl`): quem fechou, se foi bot e PR mesclado ligado ficam no cartão "Gravar issues, previsões congeladas e desfechos".
- Guardar o corpo das issues: o contrato guarda só o hash.
- Workflow do Actions e commit no branch `data`.

## Decisions

**Endpoint de listagem (`GET /repos/{owner}/{repo}/issues`), não a busca.** A lista aceita `state=all` e `since` (filtra por `updated_at`), pagina por cursor no cabeçalho `Link` e não tem teto de resultados. A busca (`/search/issues`) exclui PRs na origem, mas devolve no máximo 1.000 resultados por consulta e tem limite de 30 requisições por minuto, o que obrigaria a fatiar por datas. Custo da lista: no Airflow, a primeira execução fica na casa de 100 a 200 páginas, porque a maior parte dos itens é PR; cabe com folga no limite por hora.

**Primeira execução em duas consultas.**
- Abertas: `state=open&sort=created&direction=desc`, descartando PRs, até juntar `open_max` issues.
- Fechadas: `state=closed&sort=updated&direction=desc&since=<agora − closed_months>`, descartando PRs e guardando só as com `closed_at` dentro da janela. `since` corta por `updated_at`, que é sempre ≥ `closed_at`, então nenhuma fechada da janela fica de fora.

**Execuções seguintes em uma consulta.** `state=all&since=<cursor_since>&sort=updated&direction=asc`. O `since` é inclusivo e o cursor é o início da execução anterior, então pode haver sobreposição; ela é inofensiva porque a gravação é por número de issue.

**`body_sha256` = SHA-256 de `título + "\n\n" + corpo`** (corpo vazio quando nulo), sobre o texto cru da API. Muda quando título ou corpo mudam, e não muda com comentários ou labels.

**Gravação atômica.** Lê `issues.jsonl` para um dicionário por número, aplica as mudanças, valida cada linha e grava num arquivo temporário que substitui o original (`os.replace`). Depois grava `state.json` do mesmo jeito. Se qualquer passo falhar, nada é substituído.

**Resultado da execução.** O coletor devolve (e imprime em JSON com `--changes`) três listas de números: `new`, `edited` e `closed`. O passo do Jev usa `new + edited`; o de desfechos usa `closed`. Assim os outros passos não precisam comparar arquivos.

**Cliente HTTP próprio e pequeno, com `requests`.** Funções: sessão com token, `get` com tratamento de limite e repetição, e `paginate` seguindo `Link: rel="next"`. Limite primário: 403/429 com `X-RateLimit-Remaining: 0` → espera até `X-RateLimit-Reset`. Limite secundário: 403/429 com `Retry-After` → espera o indicado. 5xx e erros de rede: até 5 tentativas com espera exponencial. Alternativa descartada: PyGithub (dependência maior e menos controle sobre os limites).

**Nome do repositório renomeado falha em vez de seguir.** A pasta `data/<owner__nome>/` e o histórico dependem do nome; trocar sozinho espalharia dados em duas pastas. O erro mostra o nome novo para atualizar o `repos.yaml`.

**Estrutura do código.**

```
collector/
  __init__.py
  __main__.py     linha de comando
  github.py       token, sessão, get com limites, paginação, nome atual
  collect.py      primeira execução, incremental, conversão para o contrato
  store.py        leitura e gravação atômica de JSONL/JSON com validação
tests/collector/  testes com respostas gravadas (sem rede)
```

Linha de comando:

```bash
python -m collector --repo apache/airflow          # um repositório
python -m collector                                # todos os habilitados em repos.yaml
python -m collector --repo apache/airflow --changes   # imprime new/edited/closed em JSON
python -m collector --data-dir /tmp/data --config repos.yaml
```

**Token.** `GITHUB_TOKEN` (o Actions fornece) ou, localmente, `gh auth token`, como na PoC. Sem token, o limite cai para 60 requisições por hora; o coletor avisa e segue.

## Risks / Trade-offs

- [Repositório com muitos PRs gasta páginas à toa] → Medido: aceitável no Airflow. Se um repositório candidato passar de alguns milhares de páginas, trocar a primeira execução das fechadas pela busca fatiada por mês.
- [`GITHUB_TOKEN` do Actions tem limite menor que o token pessoal] → A coleta em si cabe; o peso maior (timeline para PR ligado) fica no cartão de desfechos, que deve prever lotes.
- [Issue transferida ou apagada some da lista] → Fica com o último estado conhecido em `issues.jsonl`. Aceitável para a v1; registrar se aparecer na Fase 0.
- [Relógio da máquina adiantado faria o cursor pular atualizações] → O cursor usa o horário do início da execução, e a sobreposição do `since` inclusivo cobre pequenas diferenças.

## Open Questions

- Teto de páginas por execução (proteção contra laço infinito): começar com 2.000 e ajustar com os números da Fase 0.
