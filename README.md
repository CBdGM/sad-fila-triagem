# sad-fila-triagem

SAD v3: fila priorizada de triagem de issues com o Jev. Projeto da disciplina IF1006
(Transformação Digital com IA, CIn-UFPE).

Um job diário lê as issues de repositórios públicos do GitHub (só leitura), o Jev responde
perguntas fechadas sobre cada uma, um calibrador treinado no histórico estima a chance de a issue
ser fechada sem ação e um site estático mostra a fila em três faixas: atenção primeiro, revisão
humana e provavelmente sem ação, sempre com o motivo.

A PoC que deu origem a este projeto está em
[CBdGM/sad-poc-decisao](https://github.com/CBdGM/sad-poc-decisao) (branch `app-triagem`).

## Estrutura

```
repos.yaml      repositórios observados, labels de fechamento e bots de inatividade
collector/      coletor incremental de issues (python -m collector)
outcomes/       desfechos das issues fechadas, o gabarito (python -m outcomes)
contracts/      formato de cada arquivo trocado entre as equipes (JSON Schema + exemplos)
openspec/       requisitos e mudanças no formato do OpenSpec
  specs/        o sistema como está (fonte da verdade)
  changes/      mudanças em andamento, uma pasta por mudança
tests/          testes (sem rede)
```

Ainda por vir, conforme as fases: job (`.github/workflows/`), calibrador e avaliação,
site da fila, e o branch `data` com o histórico.

## Coletor

Baixa as issues dos repositórios habilitados em `repos.yaml` e grava, por repositório,
`data/<owner__nome>/issues.jsonl` (uma linha por issue) e `data/<owner__nome>/state.json` (cursor).

- **Primeira execução** (sem `state.json`): as `first_run.open_max` abertas mais recentes e as
  fechadas dos últimos `first_run.closed_months` meses.
- **Seguintes:** só as issues atualizadas desde o cursor (novas, editadas e fechadas).
- Pull requests ficam de fora. Os arquivos são validados pelos contratos antes de gravar, e o
  cursor só avança se tudo der certo; rodar de novo não duplica nada.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m collector --repo apache/airflow             # um repositório
.venv/bin/python -m collector                                   # todos os habilitados
.venv/bin/python -m pytest -q                                   # testes
```

Durante a coleta, o andamento aparece a cada 10 páginas e no fim de cada etapa; o resumo final mostra
quantas requisições foram feitas e quantas restam no limite da hora. `--changes mudancas.json` grava
em JSON o que mudou (`new`, `edited`, `closed`), usado pelos próximos passos do job; `--changes` sem
arquivo imprime no stdout. Token: `GITHUB_TOKEN` (num `.env` ou no ambiente) ou o do `gh auth login`; sem token, o limite
do GitHub cai para 60 requisições por hora. Os dados locais ficam em `data/`, ignorada pelo git.

## Desfechos (gabarito)

Para cada issue fechada em `issues.jsonl` que ainda não tem desfecho, busca no GitHub (GraphQL, 50
issues por consulta) quem fechou, se foi bot e o PR mesclado ligado, classifica pelas regras do
gabarito (`outcomes/rules.py`, versão `gab-1`) e acrescenta a linha em
`data/<owner__nome>/outcomes.jsonl`. Grava a cada lote; rodar de novo não repete nada.

```bash
.venv/bin/python -m outcomes --repo apache/airflow   # um repositório (rode o coletor antes)
.venv/bin/python -m outcomes                         # todos os habilitados
.venv/bin/python -m outcomes --max 200               # no máximo 200 desfechos por repositório
```

O resumo final mostra quantas issues são sem ação, com ação e fora da conta, e a porcentagem "sem
ação" usada no portão da Fase 0 (≥ 15%). As regras de `gab-1` são as da proposta:

| Ordem | Regra | Classe |
|---|---|---|
| 1 | Quem fechou está em `stale_bots`, ou a issue tem label de `stale_labels` | `excluded` (`stale_bot`) |
| 2 | `state_reason` `not_planned` ou `duplicate`, ou label de `closing_labels` | `no_action` (motivo da label) |
| 3 | Fechada com PR mesclado ligado | `action` |
| 4 | Fechada como `completed` sem PR | `excluded` (`completed_without_pr`) |

Para mudar as regras (ex.: contar bot + label de motivo como "sem ação"), crie uma versão nova em
`outcomes/rules.py`; cada desfecho guarda a versão usada.

### Resultado da Fase 0 (21/11/2026, últimos 6 meses, `gab-1`)

| Repositório | % sem ação | Papel |
|---|---|---|
| microsoft/vscode | 68,4% | principal |
| microsoft/TypeScript | 48,0% | principal |
| godotengine/godot | 38,7% | principal |
| grafana/grafana | 13,7% | secundário |
| apache/airflow | 12,7% | secundário |
| kubernetes/kubernetes | 10,1% | secundário |
| elastic/elasticsearch | 9,5% | secundário |

O portão (≥ 2 repositórios com ≥ 15%) passou. A avaliação usa os principais; os secundários seguem
na coleta. `golang/go` ficou de fora porque corrige por commit do Gerrit, não por PR, e o `gab-1` só
reconhece "com ação" por PR mesclado.

## Como trabalhamos (OpenSpec)

Cada mudança grande começa como um change do OpenSpec, revisado pelo time antes do código:

1. No Claude Code, Cursor ou Copilot: `/openspec-propose <descrição>` gera `proposal.md`,
   `specs/`, `design.md` e `tasks.md` em `openspec/changes/<nome>/`.
2. O time revisa e ajusta o change (de preferência num PR).
3. `/openspec-apply-change` implementa seguindo o `tasks.md`.
4. Depois da revisão do código, `/openspec-archive-change` incorpora os requisitos em `openspec/specs/`.

Os comandos `/openspec-*` precisam do CLI. Sem instalar nada global:

```bash
npx @fission-ai/openspec@latest list
```

Para instalar global (Node 22.20 ou mais novo): `npm install -g @fission-ai/openspec@latest`.
O CLI coleta telemetria anônima por padrão; para desligar, `openspec config set telemetry.enabled false`
ou `export DO_NOT_TRACK=1`.

## Contratos

Veja [contracts/README.md](contracts/README.md). Para validar:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python contracts/validate.py
```

## Segredos

Nenhuma chave entra no código nem em commit. A chave do Jev (`TYPESAFE_API_KEY`) fica nos
*secrets* do GitHub Actions; localmente, num `.env` (já ignorado pelo `.gitignore`).
