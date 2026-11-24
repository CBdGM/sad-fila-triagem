## Why

O gabarito do projeto é o que os mantenedores fizeram com cada issue. Sem ele não há Fase 0 (o portão que decide se o projeto segue), nem calibrador, nem avaliação. O coletor já grava as issues fechadas com `state_reason` e labels, mas falta saber quem fechou, se foi bot e se há PR mesclado ligado, e classificar cada fechamento como `no_action`, `action` ou `excluded`.

## What Changes

- Novo passo de desfechos (`outcomes/`) que, para cada repositório:
  - lê as issues fechadas de `issues.jsonl` que ainda não têm desfecho para aquele fechamento (`number` + `closed_at`);
  - busca no GitHub, em lotes pela API GraphQL, quem fechou (e se é bot) e os PRs mesclados ligados à issue;
  - classifica cada fechamento pelas regras do gabarito `gab-1` (as da proposta SAD v3);
  - acrescenta as linhas em `data/<repo>/outcomes.jsonl` (contrato `outcome.schema.json`), validadas e sem repetir.
- Regras do gabarito isoladas num módulo próprio (`outcomes/rules.py`), versionadas por `rules_version`, para o Back poder mudá-las (ex.: `gab-2`) sem mexer na coleta.
- Cliente GraphQL no `collector/github.py`, com os mesmos cuidados de limite e repetição do cliente REST.
- Linha de comando `python -m outcomes`, com resumo da Fase 0 por repositório (quantas issues em cada classe e a porcentagem "sem ação").
- Testes sem rede.

## Capabilities

### New Capabilities

- `coleta-de-desfechos`: obtenção dos fatos de fechamento de cada issue no GitHub e gravação em `outcomes.jsonl`.
- `regras-do-gabarito`: classificação de um fechamento em `no_action`, `action` ou `excluded`, com motivo, a partir dos fatos e da configuração do repositório.

### Modified Capabilities

(nenhuma)

## Impact

- Código novo: `outcomes/`, `tests/outcomes/`; função `graphql` em `collector/github.py`.
- Lê `repos.yaml` (`closing_labels`, `stale_bots`, `stale_labels`) e `issues.jsonl`; grava `outcomes.jsonl`.
- Destrava a Fase 0 do Back: a porcentagem "sem ação" por repositório sai do resumo da execução.
- Fora deste change: o workflow do Actions e a decisão de passar para `gab-2` (fica com o Back, depois da Fase 0).
