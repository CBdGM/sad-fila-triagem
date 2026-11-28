## ADDED Requirements

### Requirement: Issue que saiu do repositório não conta como aberta (auditoria-dos-dados)

Uma issue com `gone_at` SHALL ser tratada como fora das abertas.

#### Scenario: Issue transferida
- **WHEN** uma issue aberta tem `gone_at`
- **THEN** ela é ignorada como aberta neste passo
