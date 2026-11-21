# Contratos de dados

Formato de cada arquivo trocado entre Back, Integração e Front. Cada contrato é um JSON Schema
(`*.schema.json`) com um exemplo válido em `examples/`. Os exemplos são fictícios e servem de dado
falso para o Front começar e de referência para o Back.

Requisitos e decisões: `openspec/changes/definir-contratos-de-dados/` (depois de arquivado, em
`openspec/specs/contratos-de-dados/`).

## Arquivos

| Arquivo | Contrato | Exemplo | Quem escreve | Quem lê | Escrita |
|---|---|---|---|---|---|
| `repos.yaml` (raiz) | `repos.schema.json` | `examples/repos.yaml` | à mão | Integração, Back | manual |
| `data/<repo>/state.json` | `state.schema.json` | `examples/state.json` | Integração | Integração | sobrescreve |
| `data/<repo>/issues.jsonl` | `issue.schema.json` (uma linha) | `examples/issues.jsonl` | Integração | Back | atualiza |
| `data/<repo>/predictions.jsonl` | `prediction.schema.json` (uma linha) | `examples/predictions.jsonl` | Integração (respostas brutas do Jev) | Back | **só acrescenta** |
| `data/<repo>/outcomes.jsonl` | `outcome.schema.json` (uma linha) | `examples/outcomes.jsonl` | Integração (regras do Back) | Back | **só acrescenta** |
| `public/queue.json` | `queue.schema.json` | `examples/queue.json` | Integração | Front | sobrescreve |
| `public/metrics.json` | `metrics.schema.json` | `examples/metrics.json` | Back → Integração | Front | sobrescreve |

`<repo>` no caminho é `owner__nome` (ex.: `data/apache__airflow/`). O cartão de escopo
(`data/<repo>/scope.md`) é texto livre escrito à mão e não tem schema.

## Regras que os arquivos garantem

- **Só acrescenta:** `predictions.jsonl` e `outcomes.jsonl` nunca têm linhas editadas ou apagadas.
- **Idempotência:** não gravar previsão repetida (mesmo `repo`, `number`, `body_sha256` e `versions`)
  nem desfecho repetido (mesmo `repo`, `number` e `closed_at`).
- **Primeira previsão congelada:** `first_seen: true` marca a primeira previsão de cada issue. `mode`
  diz se ela veio do histórico (`backfill`) ou do job diário (`daily`); só `daily` entra no teste
  prospectivo.
- **Respostas brutas:** a calibração não fica em `predictions.jsonl`; P(sem ação), motivo e faixa
  saem no `queue.json`, com a versão do calibrador.
- **Motivo da fila:** a pergunta ligada a um motivo que mais pesou no calibrador:

| Pergunta (`answers`) | Motivo (`reason`) |
|---|---|
| `usage_question` | `usage_question` |
| `enough_info` | `needs_info` |
| `in_scope` | `out_of_scope` |
| `duplicates` | `duplicate` |

`is_defect`, `actionable` e `severity` entram no calibrador, mas não viram motivo.

## Convenções

- Chaves em inglês `snake_case`; descrições dos campos em português dentro de cada schema.
- Datas em UTC, RFC 3339, terminando em `Z` (ex.: `2026-11-21T06:05:12Z`).
- Todo registro tem `schema_version` (hoje `1`). Campo opcional novo não muda a versão; remover,
  renomear ou mudar o tipo de um campo muda, e exige um change novo no OpenSpec.
- Repositório sempre como `owner/nome` com o nome atual.
- Valores fixos em inglês; o front traduz:

| Valor | Na tela |
|---|---|
| `attention` | Atenção primeiro |
| `human_review` | Revisão humana |
| `likely_no_action` | Provavelmente sem ação |
| `duplicate` | Duplicata |
| `needs_info` | Falta informação |
| `usage_question` | Pergunta de uso |
| `out_of_scope` | Fora do escopo |
| `low` / `medium` / `high` / `critical` | baixa / média / alta / crítica |

## Validar

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python contracts/validate.py                                   # todos os exemplos
.venv/bin/python contracts/validate.py queue public/queue.json           # um arquivo real
```

Sai com código 1 e lista cada erro (arquivo, linha e campo) se algo não bater. O job deve rodar a
validação antes de gravar qualquer arquivo.
