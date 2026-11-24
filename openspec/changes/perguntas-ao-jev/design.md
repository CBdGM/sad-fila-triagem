## Context

Proposta SAD v3, Fase 1: rodar a chamada A do Jev no histórico. O formato da API vem da PoC (`sad-poc-decisao`, `models.py`): `POST /v1/systemone` com `{"model", "state", "questions"}`, resposta `{"model", "answers", "usage"}`, cabeçalho `x-typesafe-request-id`, repetição em 429/529 com `retry-after`. Conferido numa chamada real em 20/10/2026 (jev-1.13.0). A limpeza é o `clean.py` da PoC, camada 1 (regex), sem mudanças, como pede a proposta.

`issues.jsonl` guarda só o hash do corpo, não o texto. Por isso o passo busca título e corpo no GitHub antes de avaliar.

## Goals / Non-Goals

**Goals:** chamada A no histórico (`backfill`) e nas abertas (`daily`); `predictions.jsonl` válido, só acrescentando, sem repetir; custo controlável.

**Non-Goals:** chamadas B e C (Fase 4); resumo via Ollama (camada 2 da PoC); calibrador e fila (Back); workflow do Actions.

## Decisions

**Módulo `evaluator/`** com `clean.py` (cópia da camada 1 da PoC, `CLEANING_VERSION = "clean-1"`), `questions.py` (`QUESTIONS_VERSION = "q1"`, as cinco perguntas), `jev.py` (cliente), `fetch.py` (título e corpo em lote) e `run.py` (seleção, chamada e gravação). Mesmo padrão de `outcomes/`.

**Perguntas `q1`.** As cinco da tabela da proposta, em inglês como na PoC. A severidade reaproveita os critérios de 4 níveis da PoC (`triage.py`). Mudar o texto de qualquer pergunta exige subir a versão.

**Seleção.** `backfill` = fechadas com desfecho mais recente `no_action` ou `action` (as `excluded` não treinam o calibrador e só gastariam tokens). `daily` = abertas. As mais recentes primeiro, para que um teto pequeno já dê uma amostra atual.

**Idempotência.** Chave `(number, body_sha256, versions.model, versions.questions, versions.cleaning)`, como diz o contrato. `first_seen` é verdadeiro quando não existe nenhuma previsão anterior para o `number`.

**Texto conferido.** O hash do título e corpo buscados é calculado com `collector.collect.body_hash`. Se não bater com `issues.jsonl`, a issue foi editada depois da coleta: fica para a próxima execução (depois do coletor), em vez de gravar um hash que não corresponde ao texto avaliado.

**Limite de contexto.** A PoC usa 30.000 tokens de estado por chamada, estimados como caracteres ÷ 4. O texto limpo é cortado em 120.000 caracteres.

**Versão explícita.** `versions.model` vem do `model` de `repos.yaml` e precisa casar com `^jev-\d+\.\d+\.\d+$`. Se o servidor responder com outra versão (`served_by`), a linha registra o que veio, e o resumo avisa.

**Gravação a cada previsão.** Cada linha é validada e acrescentada logo depois da chamada: uma falha no meio não perde o que já custou tokens.

**Linha de comando.**
```
python -m evaluator --mode backfill --repo microsoft/TypeScript --max 50
python -m evaluator --mode daily
```

## Risks / Trade-offs

- [Backfill avalia o texto atual de issues já fechadas] → limitação registrada no contrato (`mode: backfill`); só `daily` + `first_seen` entra no teste prospectivo.
- [Custo] → `--max` por repositório e resumo de tokens; a proposta estima uns 12 mil tokens por issue nas cinco chamadas (a chamada A é a menor parte).
- [Resposta do Jev muda de formato] → normalização estrita; formato inesperado para o repositório com erro claro.
- [Issue apagada ou transferida] → GraphQL devolve nulo; o passo pula e avisa.

## Open Questions

- Teto padrão do backfill por repositório (sugestão: começar com `--max 200` por repositório principal e medir o custo real).
- Se o `daily` deve reavaliar issues editadas (o contrato permite; a avaliação usa só a primeira).
