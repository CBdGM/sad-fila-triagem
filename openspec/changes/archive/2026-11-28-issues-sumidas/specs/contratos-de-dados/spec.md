## ADDED Requirements

### Requirement: Marca de issue que saiu do repositório

O contrato de issue SHALL aceitar o campo opcional `gone_at` (data UTC) para issues que saíram do repositório. Consumidores SHALL tratar uma issue com `gone_at` como fora das abertas.

#### Scenario: Issue marcada
- **WHEN** uma linha de `issues.jsonl` tem `gone_at`
- **THEN** ela passa no `issue.schema.json`
