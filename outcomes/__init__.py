"""Desfechos das issues fechadas: quem fechou, se foi bot, PR mesclado ligado e classe do gabarito.

Lê `data/<owner__nome>/issues.jsonl` (gerado pelo coletor) e `repos.yaml`, e acrescenta linhas em
`data/<owner__nome>/outcomes.jsonl` (contrato `contracts/outcome.schema.json`).
Requisitos: openspec/changes/coleta-de-desfechos/.
"""
