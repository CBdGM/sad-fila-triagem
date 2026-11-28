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
evaluator/      chamada A do Jev sobre as issues (python -m evaluator)
publisher/      monta queue.json e metrics.json para o site (python -m publisher)
audit/          auditoria diária do branch data (python -m audit)
baselines/      baselines da Fase 1: heurística e TF-IDF contra o Jev (python -m baselines)
docs/resultados/ relatórios gerados (baselines)
contracts/      formato de cada arquivo trocado entre as equipes (JSON Schema + exemplos)
openspec/       requisitos e mudanças no formato do OpenSpec
  specs/        o sistema como está (fonte da verdade)
  changes/      mudanças em andamento, uma pasta por mudança
tests/          testes (sem rede)
```

Ainda por vir, conforme as fases: calibrador e avaliação, e o site da fila.

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

## Avaliador (Jev)

Faz a chamada A do Jev (proposta SAD v3) e acrescenta as respostas em `data/<owner__nome>/predictions.jsonl`.
Para cada issue, busca título e corpo no GitHub, confere que o hash bate com `issues.jsonl`, limpa o
texto (`evaluator/clean.py`, a camada 1 do `clean.py` da PoC, versão `clean-1`) e pergunta, numa única
chamada (`evaluator/questions.py`, versão `q1`): é defeito?, dá para agir?, há informação para
reproduzir?, é pergunta de uso? e a severidade em 4 níveis.

- `--mode backfill`: fechadas com desfecho `no_action` ou `action` (o treino do calibrador). Rode os desfechos antes.
- `--mode daily`: abertas.
- Mais recentes primeiro. Não repete issue já avaliada com o mesmo texto e as mesmas versões; a primeira
  previsão de cada issue fica marcada com `first_seen`. Grava a cada issue, então uma falha não perde o que já custou tokens.
- A versão do Jev é o `model` de `repos.yaml` (nunca `jev-latest`). Precisa de `TYPESAFE_API_KEY` no `.env`.
- Credenciais coladas no texto da issue (tokens do GitHub, Azure DevOps, AWS etc.) viram `[REDACTED]` no
  `input_text` gravado (`evaluator/redact.py`); o Jev recebe o texto original.

```bash
.venv/bin/python -m evaluator --mode backfill --repo microsoft/TypeScript --max 20   # comece pequeno
.venv/bin/python -m evaluator --mode daily
```

O resumo mostra quantas previsões foram feitas, os tokens gastos e quantas faltam.

## Job diário

`.github/workflows/daily.yml` roda todo dia às 06:00 (Brasília) e também à mão (aba Actions → "Job diário" →
"Run workflow"). Ele faz checkout do branch `data`, roda coletor → desfechos → Jev nas abertas
(`--mode daily`, no máximo 200 por repositório) e commita o que mudou em `data/` nesse branch.

- Idempotente: rodar de novo ou pular um dia não duplica nada; se nada mudou, não há commit.
- Se um passo falha, o que os anteriores concluíram é commitado e o job fica marcado como falho.
- O Jev precisa do secret `TYPESAFE_API_KEY` (`gh secret set TYPESAFE_API_KEY`); sem ele, o passo é pulado com aviso.
- O agendamento do Actions pode atrasar ou pular, e é desligado após 60 dias sem atividade no repositório.

O histórico fica no branch [`data`](../../tree/data). Para usar localmente:
`git worktree add ../sad-fila-data data` e `--data-dir ../sad-fila-data/data` nos comandos.

## Fila publicada (Pages)

Depois de atualizar o branch `data`, o job diário monta e publica no GitHub Pages:

- https://cbdgm.github.io/sad-fila-triagem/queue.json — a fila (`contracts/queue.schema.json`)
- https://cbdgm.github.io/sad-fila-triagem/metrics.json — as métricas (`contracts/metrics.schema.json`)

Enquanto não há calibrador, entram as issues abertas que já têm previsão do Jev, todas na faixa
`human_review`, ordenadas por severidade e depois pela data de criação (`p_no_action`, `reason` e
`calibrator` ficam nulos; `metrics.json` sai com `evaluations` vazio). Os dois arquivos são validados
antes de gravar; se algum falhar, nada é publicado e o site anterior continua.

```bash
git worktree add ../sad-fila-data data                               # uma vez
.venv/bin/python -m publisher --data-dir ../sad-fila-data/data --out public
```

## Auditoria diária

Entre a atualização do branch `data` e a publicação, o job roda `python -m audit`, que confere os
dados sem chamar nenhuma API:

- **Erros** (dado corrompido): linha fora do contrato, desfecho ou previsão repetidos, mais de um
  `first_seen` por issue, previsão de issue desconhecida. **Impedem a publicação**: o site fica com a fila anterior.
- **Atenções** (dado parado ou crescendo): última coleta há mais de 36 h, fechada sem desfecho,
  aberta há mais de 4 dias sem previsão do Jev, dados acima de 150 MB. A fila é publicada mesmo assim.

Qualquer achado deixa o job vermelho, e o GitHub avisa por e-mail. Saída: 0 sem achados, 1 só
atenções, 2 com erro. Os limites mudam por opção (`python -m audit -h`).

```bash
.venv/bin/python -m audit --data-dir ../sad-fila-data/data
```

## Baselines da Fase 1

`python -m baselines` compara, no mesmo gabarito e com o mesmo texto que o Jev recebeu, uma heurística
(regras fixas e com pesos aprendidos), TF-IDF + regressão logística e o sinal do Jev (bruto e com
regressão logística sobre as 5 respostas). Corte temporal por repositório (70% mais antigas para
treino), AUC com intervalo de 95%, precisão média, Brier e precisão/recall/cobertura no corte de
precisão ≥ 90% escolhido no treino. Também mede só issues de autores de fora da equipe.

```bash
.venv/bin/pip install -r requirements-dev.txt          # inclui scikit-learn
.venv/bin/python -m baselines --data-dir ../sad-fila-data/data --out docs/resultados
```

Resultados em [`docs/resultados/`](docs/resultados/) (Markdown e JSON no formato do `metrics.schema.json`).

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
