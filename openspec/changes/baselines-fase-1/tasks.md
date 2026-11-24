# Tasks

- [x] 1.1 `baselines/data.py`: conjunto rotulado e corte temporal por repositório; verificar com testes de rótulo, `excluded` fora e ordem temporal
- [x] 1.2 `baselines/features.py`: sinais da heurística e regras fixas; verificar com um teste por sinal
- [x] 1.3 `baselines/models.py`: heurística com pesos, TF-IDF + regressão (C por validação cruzada no treino), referências do Jev
- [x] 1.4 `baselines/metrics.py`: AUC com IC, PR-AUC, Brier, corte por precisão-alvo escolhido no treino; verificar com casos conhecidos
- [x] 2.1 `python -m baselines` com relatório Markdown e JSON no formato do `metrics.schema.json`; verificar com teste de CLI em dados sintéticos
- [x] 2.2 Rodar nos dados reais e registrar o relatório em `docs/resultados/`
- [x] 2.3 Seção no README e `scikit-learn` em `requirements-dev.txt`

## Workflow follow-up

- Arquivar o change depois do merge.
