## ADDED Requirements

### Requirement: Issues que saíram do repositório

Ao fim de cada coleta, o coletor SHALL conferir se as issues abertas ainda existem no repositório e SHALL marcar com `gone_at` as que o GitHub informa como inexistentes ali (transferidas, apagadas ou convertidas em discussão), sem apagar a linha. Uma falha nessa conferência SHALL ser só um aviso.

#### Scenario: Issue transferida
- **WHEN** uma issue aberta em `issues.jsonl` não existe mais no repositório
- **THEN** ela ganha `gone_at` e aparece em `gone` no resumo da coleta

#### Scenario: Issue volta
- **WHEN** uma issue marcada com `gone_at` reaparece na coleta incremental
- **THEN** a linha é regravada sem `gone_at`

#### Scenario: Erro do GitHub na conferência
- **WHEN** a consulta de conferência falha
- **THEN** a coleta grava normalmente, nada é marcado e um aviso é mostrado
