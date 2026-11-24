# perguntas-ao-jev Specification

## Purpose

Fazer a chamada A do Jev sobre cada issue (texto limpo, cinco perguntas, versão fixa) e gravar as respostas em `predictions.jsonl`, para que o calibrador aprenda no histórico e a fila diária avalie as issues abertas.

## Requirements

### Requirement: Seleção das issues por modo

O passo SHALL avaliar, no modo `backfill`, as issues fechadas cujo desfecho mais recente é `no_action` ou `action`, e, no modo `daily`, as issues abertas de `issues.jsonl`. Issues com desfecho `excluded` SHALL ficar de fora do `backfill`.

#### Scenario: Backfill só com desfechos que contam
- **WHEN** o repositório tem uma issue fechada `no_action`, uma `action` e uma `excluded`
- **THEN** o modo `backfill` avalia só as duas primeiras

#### Scenario: Daily só com abertas
- **WHEN** o modo é `daily`
- **THEN** só issues com `state` `open` são avaliadas

### Requirement: Não repetir previsões

O passo SHALL pular uma issue que já tem previsão com o mesmo `body_sha256` e as mesmas `versions` (`model`, `questions`, `cleaning`). Previsões existentes SHALL nunca ser reescritas.

#### Scenario: Segunda execução
- **WHEN** o passo roda duas vezes seguidas sem mudança nas issues
- **THEN** a segunda execução não chama o Jev e não grava nada

#### Scenario: Issue editada
- **WHEN** o `body_sha256` de uma issue mudou desde a última previsão
- **THEN** a issue é avaliada de novo e a linha nova tem `first_seen` falso

### Requirement: Texto conferido e limpo

O passo SHALL buscar título e corpo no GitHub, calcular o hash como o coletor e pular (com aviso) a issue cujo hash não bate com `issues.jsonl`. O texto enviado SHALL ser o título e o corpo limpos pelo `clean-1`, cortado no limite de contexto do Jev.

#### Scenario: Issue editada depois da coleta
- **WHEN** o hash do texto buscado difere do de `issues.jsonl`
- **THEN** a issue não é avaliada nesta execução e aparece na lista de puladas

### Requirement: Chamada A com versão explícita

O passo SHALL enviar as cinco perguntas da chamada A numa única requisição, com o `model` de `repos.yaml`, e SHALL recusar `jev-latest`. Respostas em formato inesperado SHALL interromper o repositório com erro claro, mantendo o que já foi gravado.

#### Scenario: Modelo sem versão
- **WHEN** `repos.yaml` tem `model: jev-latest`
- **THEN** o passo para antes de chamar o Jev, com mensagem pedindo uma versão explícita

#### Scenario: Resposta normalizada
- **WHEN** o Jev responde as cinco perguntas
- **THEN** a linha grava as quatro probabilidades `noul` e a severidade com as 4 probabilidades na ordem [low, medium, high, critical] e o nível mais provável

### Requirement: Gravação conforme o contrato

Cada previsão SHALL ser validada por `prediction.schema.json` e acrescentada a `predictions.jsonl` assim que pronta, com `mode`, `first_seen` (verdadeiro só na primeira previsão da issue), `versions`, `provenance` (versão que respondeu, id da requisição, latência e tokens) e `input_text`.

#### Scenario: Falha no meio
- **WHEN** o Jev falha depois de algumas issues avaliadas
- **THEN** as previsões já feitas continuam gravadas e a próxima execução continua das que faltam

### Requirement: Teto de custo

O passo SHALL aceitar um teto de issues por repositório e execução e SHALL informar no fim quantas issues avaliou, quantos tokens gastou e quantas faltam.

#### Scenario: Teto atingido
- **WHEN** há 10 issues pendentes e o teto é 3
- **THEN** só 3 são avaliadas e o resumo informa que faltam 7
