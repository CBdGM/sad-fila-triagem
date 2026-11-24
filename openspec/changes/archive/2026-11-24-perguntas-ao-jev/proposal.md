## Why

A Fase 1 da proposta SAD v3 roda a chamada A do Jev no histórico para treinar o calibrador e comparar com as heurísticas. Sem as respostas do Jev gravadas em `predictions.jsonl`, o Back não tem entrada para o calibrador, e o job diário não tem o que pôr na fila. A Fase 0 passou (VS Code, TypeScript, Godot), então este é o próximo passo da Integração.

## What Changes

- Novo passo do avaliador (`evaluator/`) que, para cada repositório:
  - escolhe as issues a avaliar: no modo `backfill`, as fechadas com desfecho `no_action` ou `action` (as que treinam o calibrador); no modo `daily`, as abertas;
  - pula o que já tem previsão com o mesmo `body_sha256` e as mesmas versões (modelo, perguntas, limpeza);
  - busca título e corpo no GitHub (GraphQL, em lotes), confere que o hash bate com `issues.jsonl` e limpa o texto com o `clean.py` da PoC, sem mudanças (`clean-1`);
  - faz a chamada A ao Jev (`/v1/systemone`) com as cinco perguntas da proposta (`q1`): defeito, acionável, informação suficiente, pergunta de uso e severidade em 4 níveis;
  - acrescenta a linha em `data/<repo>/predictions.jsonl` (contrato `prediction.schema.json`), com `first_seen` só na primeira previsão da issue e a procedência devolvida pelo servidor.
- Versão do Jev explícita, lida do `model` de `repos.yaml` (nunca `jev-latest`).
- Linha de comando `python -m evaluator` com `--mode`, `--repo`, `--max` (teto de custo) e resumo de tokens gastos.
- Testes sem rede, com o Jev e o GitHub simulados.

## Capabilities

### New Capabilities

- `perguntas-ao-jev`: seleção das issues, montagem do texto, chamada A ao Jev e gravação em `predictions.jsonl`.

### Modified Capabilities

(nenhuma)

## Impact

- Código novo: `evaluator/`, `tests/evaluator/`.
- Lê `repos.yaml`, `issues.jsonl` e `outcomes.jsonl`; grava `predictions.jsonl`.
- Precisa de `TYPESAFE_API_KEY` (`.env` ou secrets do Actions) só para rodar de verdade; os testes não precisam.
- Fora deste change: chamadas B (escopo) e C (duplicatas), que são da Fase 4; o calibrador (Back); o workflow do Actions.
