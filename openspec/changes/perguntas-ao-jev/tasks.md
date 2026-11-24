# Tasks

## 1. Texto

- [x] 1.1 `evaluator/clean.py` com a camada 1 do `clean.py` da PoC, sem mudanças, e `CLEANING_VERSION = "clean-1"`; verificar com testes de template, comando de bot e bloco de código longo
- [x] 1.2 `evaluator/fetch.py`: título e corpo em lote pelo GraphQL, pulando issue nula; verificar com teste simulado

## 2. Jev

- [x] 2.1 `evaluator/questions.py` com as cinco perguntas da chamada A e `QUESTIONS_VERSION = "q1"`
- [x] 2.2 `evaluator/jev.py`: chamada A com versão explícita, repetição em 429/529, normalização das respostas e procedência; verificar com respostas gravadas no formato da PoC

## 3. Execução (`evaluator/run.py`)

- [x] 3.1 Seleção por modo e pendentes pela chave de idempotência; verificar com testes de backfill, daily e issue editada
- [x] 3.2 Conferência de hash, corte do texto, gravação validada a cada previsão e teto; verificar com testes de hash divergente, falha no meio e teto
- [x] 3.3 Idempotência e `first_seen`; verificar com teste de duas execuções seguidas

## 4. Linha de comando e documentação

- [x] 4.1 `python -m evaluator` com `--mode`, `--repo`, `--config`, `--data-dir` e `--max`, resumo de issues, tokens e pendentes; erro claro sem `TYPESAFE_API_KEY` e com `jev-latest`; verificar com teste de CLI
- [x] 4.2 Seção "Avaliador (Jev)" no `README.md`

## 5. Verificação real

- [x] 5.1 Com a chave: rodar `--mode backfill --max 20` num repositório principal, conferir `contracts/validate.py` no `predictions.jsonl` e rodar de novo para confirmar que nada repete

## Workflow follow-up

- Arquivar o change com `openspec archive perguntas-ao-jev` depois do merge.
