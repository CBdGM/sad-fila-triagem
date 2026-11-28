# publicacao-da-fila Specification

## Purpose

Montar e publicar todo dia no GitHub Pages a fila (`queue.json`) e as métricas (`metrics.json`) a partir do branch `data`, validadas pelos contratos, para que o site mostre as issues abertas avaliadas pelo Jev.

## Requirements

### Requirement: Fila a partir das abertas avaliadas

O passo SHALL montar `queue.json` com as issues abertas de `issues.jsonl` que têm ao menos uma previsão em `predictions.jsonl`, usando a previsão mais recente de cada issue. Issues abertas sem previsão SHALL ficar de fora e SHALL ser contadas no resumo.

#### Scenario: Aberta sem previsão
- **WHEN** um repositório tem 3 abertas e só 2 com previsão
- **THEN** a fila tem as 2 e o resumo informa 1 aberta sem previsão

#### Scenario: Issue fechada
- **WHEN** uma issue com previsão está fechada em `issues.jsonl`
- **THEN** ela não aparece na fila

#### Scenario: Issue reavaliada
- **WHEN** uma aberta tem duas previsões
- **THEN** a severidade do item vem da previsão mais recente

### Requirement: Faixa única sem calibrador

Enquanto não houver calibrador, todos os itens SHALL ir para `human_review`, com `p_no_action` e `reason` nulos e `evidence` vazio, e cada repositório SHALL ter `calibrator: null` e as contagens das três faixas.

#### Scenario: Contagens
- **WHEN** um repositório tem 5 itens na fila
- **THEN** `counts` é `{"attention": 0, "human_review": 5, "likely_no_action": 0}`

### Requirement: Ordem dos itens

Os itens SHALL vir ordenados por severidade, da mais alta para a mais baixa, e, dentro da mesma severidade, por `created_at`, da mais antiga para a mais nova.

#### Scenario: Severidade antes da data
- **WHEN** há uma issue `critical` recente e uma `low` antiga
- **THEN** a `critical` vem primeiro

### Requirement: Nada publicado fora do contrato

`queue.json` e `metrics.json` SHALL ser validados pelos contratos antes de gravar. Se algum falhar, nada SHALL ser gravado em `public/` e o comando SHALL terminar com erro, para o deploy não acontecer e o site anterior continuar.

#### Scenario: Fila inválida
- **WHEN** a fila montada não passa no `queue.schema.json`
- **THEN** o comando sai com erro e `public/` fica como estava

### Requirement: Publicação diária no Pages

O job diário SHALL publicar `public/` (`queue.json`, `metrics.json` e `index.html`) no GitHub Pages depois de atualizar o branch `data`, num job com permissão só de Pages.

#### Scenario: Execução do job
- **WHEN** o job diário termina a atualização dos dados
- **THEN** `https://cbdgm.github.io/sad-fila-triagem/queue.json` passa a servir a fila nova

### Requirement: Issue que saiu do repositório não conta como aberta (publicacao-da-fila)

Uma issue com `gone_at` SHALL ser tratada como fora das abertas.

#### Scenario: Issue transferida
- **WHEN** uma issue aberta tem `gone_at`
- **THEN** ela é ignorada como aberta neste passo
