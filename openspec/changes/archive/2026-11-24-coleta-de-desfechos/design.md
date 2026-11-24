## Context

Ver `proposal.md` (Why). Contrato de saída: `contracts/outcome.schema.json`. Entradas: `issues.jsonl` (gerado pelo coletor) e `repos.yaml`. Medição feita em 21/11/2026 no `apache/airflow`:

| Medida | Valor |
|---|---|
| Issues fechadas em 6 meses | 1.280 |
| Custo de uma consulta GraphQL com 50 issues e seus eventos | 1 ponto (limite de 5.000 por hora), 2,4 s |
| Issues com 50 ou mais eventos de fechamento/referência (lote de 50) | 0 |

No GraphQL, o login de bot vem sem o sufixo (`github-actions`); na API REST e no `repos.yaml`, com (`github-actions[bot]`).

## Goals / Non-Goals

**Goals:**
- Desfechos para todas as issues fechadas coletadas, baratos em requisições e retomáveis.
- Regras do gabarito separadas da coleta, testáveis e versionadas.

**Non-Goals:**
- Guardar as labels exatamente no momento do fechamento: usamos as labels atuais de `issues.jsonl` (limitação registrada; labels raramente mudam depois do fechamento).
- Escolher entre `gab-1` e `gab-2`: fica com o Back depois da Fase 0.

## Decisions

**GraphQL em lotes de 50 issues.** Uma consulta por lote, com um alias por issue, pede os eventos `ClosedEvent` (quem fechou e o `closer`) e `CrossReferencedEvent` (PRs que referenciam a issue). Alternativa descartada: REST, que exige `GET /issues/{n}` mais a timeline por issue (2.500+ requisições no Airflow, mais que o limite do token do Actions por hora).

**Últimos 50 eventos por issue.** Pega o fechamento mais recente e os PRs que referenciam. Se uma issue vier com 50 eventos (pode haver mais), o passo registra um aviso; na medição não houve nenhuma.

**Quem fechou = ator do último `ClosedEvent`.** Bot quando `__typename` é `Bot` ou o login termina em `[bot]`; o login de bot é normalizado para terminar em `[bot]`.

**PR ligado.** Primeiro o `closer` do último `ClosedEvent`, se for PR mesclado do mesmo repositório; senão, o primeiro `CrossReferencedEvent` cuja origem é PR mesclado do mesmo repositório (o mesmo critério da PoC para achar o PR da correção).

**Pendentes calculados pelos arquivos, não pela saída do coletor.** Pendente = issue fechada em `issues.jsonl` sem linha em `outcomes.jsonl` com o mesmo `number` e `closed_at`. Assim o passo se recupera sozinho de execuções puladas e não depende de receber a lista `closed`.

**Gravação por lote.** Depois de cada lote, as linhas novas são validadas e o arquivo é regravado de forma atômica com elas no fim (só acrescenta). Se um lote falhar, os anteriores já estão salvos.

**Regras em `outcomes/rules.py`, funções puras.** `classify(facts, repo_cfg) -> (label, reason, exclusion_reason)`, sem rede nem arquivo, com `RULES_VERSION = "gab-1"`. Ordem: inatividade → sem ação → com ação/completed sem PR. É o arquivo que o Back muda para uma `gab-2`.

**Estrutura.**

```
outcomes/
  __init__.py
  __main__.py   linha de comando e resumo da Fase 0
  fetch.py      consulta GraphQL em lotes e extração dos fatos
  rules.py      regras do gabarito (gab-1)
  run.py        pendentes, lotes, gravação
collector/github.py   + graphql(s, query, variables)
tests/outcomes/
```

```bash
python -m outcomes                          # todos os repositórios habilitados
python -m outcomes --repo apache/airflow    # um repositório
python -m outcomes --max 200                # no máximo 200 desfechos por repositório nesta execução
```

## Risks / Trade-offs

- [Labels atuais em vez das do fechamento] → Registrado como limitação; afeta pouco o gabarito.
- [`CrossReferencedEvent` pode trazer PR que só menciona a issue] → Só conta se mesclado e do mesmo repositório, e o `closer` tem prioridade. Mesmo critério da PoC.
- [Limite secundário do GraphQL em lotes grandes] → Lotes de 50 e o mesmo tratamento de `Retry-After` do REST.
- [Issue apagada ou transferida] → O GraphQL devolve nulo para ela; o passo pula e avisa, sem gravar.

## Open Questions

- Tamanho do lote (50) pode subir se o custo continuar em 1 ponto; ajustar com os números dos outros repositórios.

### Achados da amostra manual (21/11/2026) — candidatos a `gab-2`, ainda não implementados

Amostra de 30 desfechos (10 por repositório principal: 4 sem ação, 4 com ação, 2 fora, semente 42):
25 parecem certos, 3 errados, 2 duvidosos; os 12 "com ação" acertaram.

- **Spam fechado como `completed`** (2 de 2 "fora" do VS Code eram lixo fechado pelo autor): caem em
  `completed_without_pr`, mas deveriam ser sem ação. Efeito: a % sem ação sai menor que a real.
- **Sem ação com PR mesclado ligado** (ex.: TypeScript #65048, fechada como não planejada em 30/10 e
  corrigida por PR em 04/11): VS Code 189 de 7.129, TypeScript 16 de 225, Godot 20 de 609. Nem todo é erro
  (às vezes o PR é só relacionado), mas são ambíguos. Proposta: `no_action` + `merged_pr` → `excluded`.
- **Godot:** a label `archived` vai em toda não planejada, então o motivo `other` do Godot não informa nada.
- **Go fora:** corrige por commit do Gerrit (`closer` é `Commit`), que o `gab-1` não reconhece como ação.
