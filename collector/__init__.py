"""Coletor incremental de issues do GitHub (SAD v3).

Lê os repositórios de `repos.yaml`, baixa as issues (primeira execução com tetos, depois só o que
mudou desde o cursor) e grava `data/<owner__nome>/issues.jsonl` e `state.json` no formato de
`contracts/`. Requisitos: openspec/changes/coletor-incremental/.
"""
