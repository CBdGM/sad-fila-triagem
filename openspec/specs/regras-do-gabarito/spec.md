# regras-do-gabarito Specification

## Purpose

Definir, de forma versionada e testável, como um fechamento de issue vira classe do gabarito (`no_action`, `action` ou `excluded`) com motivo, conforme a proposta SAD v3.

## Requirements

### Requirement: Regras versionadas
Cada classificação MUST registrar a versão das regras usadas (`rules_version`). Esta versão é `gab-1`, a regra da proposta: todo fechamento por inatividade fica fora da conta.

#### Scenario: Versão registrada
- **WHEN** um desfecho é classificado
- **THEN** a linha traz `rules_version: gab-1`

### Requirement: Inatividade fica fora da conta
Um fechamento MUST ser `excluded` com `exclusion_reason: stale_bot` quando quem fechou está em `stale_bots` do repositório ou quando a issue tem uma label de `stale_labels`. Essa regra vem antes das demais.

#### Scenario: Bot de inatividade com label de motivo
- **WHEN** `github-actions[bot]` (em `stale_bots`) fecha uma issue que tinha a label `pending-response`
- **THEN** o desfecho é `excluded` com `stale_bot`, porque `gab-1` exclui todo fechamento por inatividade

#### Scenario: Label de inatividade com bot que também fecha a pedido
- **WHEN** `kubernetes-prow[bot]` fecha uma issue com a label `lifecycle/rotten`
- **THEN** o desfecho é `excluded` com `stale_bot`

### Requirement: Sem ação
Fora os casos de inatividade, um fechamento MUST ser `no_action` quando o `state_reason` é `not_planned` ou `duplicate`, ou quando a issue tem uma label de `closing_labels`. O motivo MUST vir da label mapeada; sem label, `duplicate` para `state_reason: duplicate` e `other` para `not_planned`.

#### Scenario: Duplicata pelo GitHub
- **WHEN** a issue fecha com `state_reason: duplicate` e sem label de fechamento
- **THEN** o desfecho é `no_action` com motivo `duplicate`

#### Scenario: Completed com label de motivo
- **WHEN** a issue fecha como `completed`, mas tem a label `info-needed` mapeada para `needs_info`
- **THEN** o desfecho é `no_action` com motivo `needs_info`

#### Scenario: Not planned sem label
- **WHEN** a issue fecha como `not_planned` sem label de fechamento
- **THEN** o desfecho é `no_action` com motivo `other`

### Requirement: Prioridade entre motivos
Quando a issue tem mais de uma label de fechamento, o motivo MUST seguir a ordem `duplicate`, `needs_info`, `usage_question`, `out_of_scope`, `other`.

#### Scenario: Duas labels
- **WHEN** a issue tem labels mapeadas para `other` e para `duplicate`
- **THEN** o motivo é `duplicate`

### Requirement: Com ação
Fora os casos anteriores, um fechamento `completed` (ou sem `state_reason`) MUST ser `action` se houver `merged_pr`, e `excluded` com `completed_without_pr` se não houver.

#### Scenario: Corrigida por PR
- **WHEN** a issue fecha como `completed` com `merged_pr: 74853`
- **THEN** o desfecho é `action`

#### Scenario: Completed sem PR
- **WHEN** a issue fecha como `completed` sem PR mesclado ligado
- **THEN** o desfecho é `excluded` com `completed_without_pr`
