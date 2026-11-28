## ADDED Requirements

### Requirement: Issue que saiu do repositório não conta como aberta (publicacao-da-fila)

Uma issue com `gone_at` SHALL ser tratada como fora das abertas.

#### Scenario: Issue transferida
- **WHEN** uma issue aberta tem `gone_at`
- **THEN** ela é ignorada como aberta neste passo
