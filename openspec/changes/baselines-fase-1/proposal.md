## Why

O portão da Fase 1 da proposta SAD v3 diz que o Jev com calibrador precisa superar uma heurística simples com folga e ficar perto de um LLM forte. Sem baselines medidos nos mesmos dados e com o mesmo gabarito, não há como dizer se o Jev agrega algo. O backfill (12.454 issues fechadas com texto, respostas do Jev e desfecho) já permite medir isso agora, antes de o Back investir no calibrador.

Card do Back "[Back] Baselines: heurística, TF-IDF, Laya e LLM forte", adiantado pela Integração na parte que roda localmente e sem custo (heurística e TF-IDF). Laya e LLM forte ficam para depois.

## What Changes

- Novo módulo `baselines/` (`python -m baselines`) que, a partir do branch `data`:
  - monta o conjunto rotulado: issues fechadas com desfecho `no_action` (positivo) ou `action`, com o texto que o Jev recebeu (`input_text` do backfill) e as respostas do Jev;
  - separa treino e teste por tempo dentro de cada repositório (70% mais antigas por `created_at` para treino, 30% mais recentes para teste);
  - avalia, nos mesmos testes: heurística por regras fixas (sem treino), heurística com pesos aprendidos (regressão logística sobre os mesmos sinais), TF-IDF + regressão logística, e duas referências do Jev (a resposta "é defeito?" invertida, sem treino, e uma regressão logística sobre as 5 respostas);
  - mede AUC com intervalo de 95% (bootstrap), precisão média (PR-AUC), Brier e, num corte escolhido no treino para precisão ≥ 90% em "sem ação", a precisão, o recall e a cobertura no teste;
  - grava um relatório em Markdown e as avaliações no formato `evaluation` do `metrics.schema.json`.
- `scikit-learn` entra em `requirements-dev.txt` (não é usado pelo job diário).

## Capabilities

### New Capabilities

- `baselines`: conjunto rotulado, corte temporal, modelos de comparação e métricas da Fase 1.

### Modified Capabilities

(nenhuma)

## Impact

- Código novo: `baselines/`, `tests/baselines/`; relatório em `docs/resultados/`.
- Só lê o branch `data`; não muda o job nem a fila.
- O calibrador oficial continua com o Back; a regressão sobre as respostas do Jev aqui é só referência.
