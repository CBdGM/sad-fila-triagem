# Tasks

## 1. Cliente GraphQL

- [x] 1.1 `graphql(s, query, variables)` em `collector/github.py`, com limite (403/429, `Retry-After`), repetição em 5xx, contagem de uso e erro claro quando a resposta traz `errors`; verificar com testes simulados

## 2. Regras do gabarito (`outcomes/rules.py`)

- [x] 2.1 `classify` com a ordem inatividade → sem ação → com ação/completed sem PR e `RULES_VERSION = "gab-1"`; verificar com um teste por cenário do spec `regras-do-gabarito`
- [x] 2.2 Prioridade entre motivos quando há mais de uma label; verificar com teste

## 3. Fatos do GitHub (`outcomes/fetch.py`)

- [x] 3.1 Montar a consulta em lote (um alias por issue) e extrair quem fechou, se é bot (login normalizado com `[bot]`) e o PR mesclado ligado; verificar com respostas gravadas do Airflow (fechada por PR, por bot, à mão com PR não mesclado)
- [x] 3.2 Pular issue que volta nula e avisar quando uma issue vier com 50 eventos; verificar com teste

## 4. Execução (`outcomes/run.py`)

- [x] 4.1 Calcular pendentes por `number` + `closed_at` a partir de `issues.jsonl` e `outcomes.jsonl`; verificar com teste de issue reaberta e fechada de novo
- [x] 4.2 Processar em lotes, validar e gravar a cada lote (só acrescenta), com teto `--max`; verificar com testes de falha no meio e de teto
- [x] 4.3 Idempotência; verificar com teste de duas execuções seguidas

## 5. Linha de comando e documentação

- [x] 5.1 `python -m outcomes` com `--repo`, `--config`, `--data-dir` e `--max`, andamento e resumo da Fase 0; verificar com teste de CLI
- [x] 5.2 Seção "Desfechos" no `README.md`; verificar que os comandos documentados rodam como escritos

## 6. Verificação real

- [x] 6.1 Rodar no `apache/airflow` sobre as issues já coletadas, conferir `contracts/validate.py` no `outcomes.jsonl`, rodar de novo para confirmar que nada repete e registrar a porcentagem "sem ação"

## Workflow follow-up

- Arquivar o change com `openspec archive coleta-de-desfechos` depois do merge.
