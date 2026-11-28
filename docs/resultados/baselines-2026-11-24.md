# Baselines da Fase 1 (2026-11-24)

Gerado por `python -m baselines` a partir do branch `data` (gabarito `gab-1`, Jev `q1`/`clean-1`).
Positivo = fechada **sem ação**. Corte temporal por repositório: 70% mais antigas (por `created_at`) para treino, 30% mais recentes para teste. Todo ajuste usa só o treino.

Precisão, recall e cobertura usam o corte escolhido no treino para precisão ≥ 90% em "sem ação" (a precisão-alvo da proposta) e aplicado ao teste; "—" = o treino não atinge o alvo.

## microsoft/vscode

Treino 7288 (2015-12-01 a 2026-09-01) · teste 3123 (2026-09-01 a 2026-11-20) · sem ação no teste: 55%

| Modelo | AUC [IC 95%] | Precisão média | Brier | Precisão @corte | Recall @corte | Cobertura |
|---|---|---|---|---|---|---|
| Heurística (regras fixas) | 0.448 [0.428–0.468] | 0.527 | — | — | — | — |
| Heurística (pesos aprendidos) | 0.710 [0.692–0.728] | 0.771 | 0.248 | 77% | 41% | 29% |
| TF-IDF + regressão logística | 0.857 [0.844–0.870] | 0.899 | 0.163 | 85% | 75% | 48% |
| Jev bruto (1 − é defeito) | 0.622 [0.602–0.641] | 0.628 | — | 76% | 1% | 1% |
| Jev + regressão logística (referência) | 0.809 [0.794–0.824] | 0.857 | 0.206 | 83% | 63% | 41% |

Só autores de fora da equipe (sem OWNER/MEMBER/COLLABORATOR): 2182 issues no teste, sem ação: 70%. Mesmos modelos e cortes.

| Modelo | AUC [IC 95%] | Precisão média | Precisão @corte | Recall @corte | Cobertura |
|---|---|---|---|---|---|
| Heurística (regras fixas) | 0.529 [0.502–0.555] | 0.719 | — | — | — |
| Heurística (pesos aprendidos) | 0.676 [0.653–0.698] | 0.842 | 80% | 44% | 38% |
| TF-IDF + regressão logística | 0.872 [0.856–0.887] | 0.942 | 89% | 82% | 64% |
| Jev bruto (1 − é defeito) | 0.694 [0.668–0.717] | 0.820 | 100% | 1% | 1% |
| Jev + regressão logística (referência) | 0.835 [0.818–0.851] | 0.924 | 91% | 68% | 52% |

Notas: Heurística (regras fixas): sem treino; TF-IDF + regressão logística: C=3.0 (validação cruzada no treino); Jev bruto (1 − é defeito): 1 − is_defect, sem treino.

## microsoft/TypeScript

Treino 327 (2015-05-12 a 2026-09-27) · teste 140 (2026-09-27 a 2026-11-20) · sem ação no teste: 36%

| Modelo | AUC [IC 95%] | Precisão média | Brier | Precisão @corte | Recall @corte | Cobertura |
|---|---|---|---|---|---|---|
| Heurística (regras fixas) | 0.529 [0.449–0.613] | 0.401 | — | — | — | — |
| Heurística (pesos aprendidos) | 0.582 [0.469–0.679] | 0.526 | 0.252 | — | — | — |
| TF-IDF + regressão logística | 0.677 [0.585–0.769] | 0.506 | 0.219 | 0% | 0% | 1% |
| Jev bruto (1 − é defeito) | 0.618 [0.521–0.718] | 0.531 | — | — | — | — |
| Jev + regressão logística (referência) | 0.581 [0.474–0.679] | 0.510 | 0.238 | — | — | — |

Só autores de fora da equipe (sem OWNER/MEMBER/COLLABORATOR): 140 issues no teste, sem ação: 36%. Mesmos modelos e cortes.

| Modelo | AUC [IC 95%] | Precisão média | Precisão @corte | Recall @corte | Cobertura |
|---|---|---|---|---|---|
| Heurística (regras fixas) | 0.529 [0.449–0.613] | 0.401 | — | — | — |
| Heurística (pesos aprendidos) | 0.582 [0.469–0.679] | 0.526 | — | — | — |
| TF-IDF + regressão logística | 0.677 [0.585–0.769] | 0.506 | 0% | 0% | 1% |
| Jev bruto (1 − é defeito) | 0.618 [0.521–0.718] | 0.531 | — | — | — |
| Jev + regressão logística (referência) | 0.581 [0.474–0.679] | 0.510 | — | — | — |

Notas: Heurística (regras fixas): sem treino; TF-IDF + regressão logística: C=10.0 (validação cruzada no treino); Jev bruto (1 − é defeito): 1 − is_defect, sem treino.

## godotengine/godot

Treino 1102 (2018-04-08 a 2026-08-27) · teste 473 (2026-08-27 a 2026-11-21) · sem ação no teste: 39%

| Modelo | AUC [IC 95%] | Precisão média | Brier | Precisão @corte | Recall @corte | Cobertura |
|---|---|---|---|---|---|---|
| Heurística (regras fixas) | 0.438 [0.385–0.492] | 0.388 | — | — | — | — |
| Heurística (pesos aprendidos) | 0.599 [0.548–0.653] | 0.520 | 0.228 | — | — | — |
| TF-IDF + regressão logística | 0.750 [0.707–0.794] | 0.664 | 0.210 | 90% | 10% | 4% |
| Jev bruto (1 − é defeito) | 0.592 [0.533–0.649] | 0.570 | — | — | — | — |
| Jev + regressão logística (referência) | 0.624 [0.568–0.676] | 0.591 | 0.226 | 86% | 6% | 3% |

Só autores de fora da equipe (sem OWNER/MEMBER/COLLABORATOR): 444 issues no teste, sem ação: 42%. Mesmos modelos e cortes.

| Modelo | AUC [IC 95%] | Precisão média | Precisão @corte | Recall @corte | Cobertura |
|---|---|---|---|---|---|
| Heurística (regras fixas) | 0.442 [0.390–0.493] | 0.413 | — | — | — |
| Heurística (pesos aprendidos) | 0.599 [0.544–0.650] | 0.543 | — | — | — |
| TF-IDF + regressão logística | 0.748 [0.701–0.791] | 0.681 | 90% | 10% | 5% |
| Jev bruto (1 − é defeito) | 0.587 [0.527–0.644] | 0.585 | — | — | — |
| Jev + regressão logística (referência) | 0.629 [0.575–0.686] | 0.614 | 86% | 6% | 3% |

Notas: Heurística (regras fixas): sem treino; TF-IDF + regressão logística: C=10.0 (validação cruzada no treino); Jev bruto (1 − é defeito): 1 − is_defect, sem treino.

## Todos (3 principais)

Treino 8717 (2015-12-01 a 2026-08-27) · teste 3736 (2026-09-01 a 2026-11-21) · sem ação no teste: 52%

| Modelo | AUC [IC 95%] | Precisão média | Brier | Precisão @corte | Recall @corte | Cobertura |
|---|---|---|---|---|---|---|
| Heurística (regras fixas) | 0.466 [0.449–0.484] | 0.511 | — | — | — | — |
| Heurística (pesos aprendidos) | 0.696 [0.680–0.713] | 0.735 | 0.246 | 79% | 35% | 23% |
| TF-IDF + regressão logística | 0.830 [0.816–0.843] | 0.871 | 0.171 | 86% | 66% | 40% |
| Jev bruto (1 − é defeito) | 0.638 [0.621–0.655] | 0.621 | — | 62% | 0% | 0% |
| Jev + regressão logística (referência) | 0.784 [0.769–0.798] | 0.830 | 0.203 | 87% | 50% | 30% |

Só autores de fora da equipe (sem OWNER/MEMBER/COLLABORATOR): 2766 issues no teste, sem ação: 64%. Mesmos modelos e cortes.

| Modelo | AUC [IC 95%] | Precisão média | Precisão @corte | Recall @corte | Cobertura |
|---|---|---|---|---|---|
| Heurística (regras fixas) | 0.537 [0.516–0.559] | 0.669 | — | — | — |
| Heurística (pesos aprendidos) | 0.684 [0.664–0.704] | 0.801 | 82% | 38% | 30% |
| TF-IDF + regressão logística | 0.851 [0.835–0.864] | 0.917 | 89% | 71% | 51% |
| Jev bruto (1 − é defeito) | 0.708 [0.687–0.728] | 0.795 | 100% | 0% | 0% |
| Jev + regressão logística (referência) | 0.816 [0.799–0.831] | 0.898 | 93% | 54% | 37% |

Notas: Heurística (regras fixas): sem treino; TF-IDF + regressão logística: C=3.0 (validação cruzada no treino); Jev bruto (1 − é defeito): 1 − is_defect, sem treino.

## Como ler

- **AUC**: chance de o modelo dar nota maior a uma "sem ação" do que a uma "com ação" sorteadas; 0,5 = acaso.
- **Precisão média**: área sob a curva precisão × recall; compare com a taxa-base de "sem ação" do teste.
- **Brier**: erro quadrático das probabilidades (menor é melhor); só para modelos que dão probabilidade.
- **Jev + regressão logística** é uma referência do que um calibrador simples faria com as 5 respostas, não o calibrador do Back.

## Limitações

- No VS Code, relatórios gerados pelo próprio editor (tabelas "System Info", lista de extensões) aparecem mais entre as "sem ação". O TF-IDF pode estar aprendendo esse formato, não o conteúdo; a limpeza `clean-1` não remove essas tabelas.
- Issues abertas pela própria equipe (OWNER/MEMBER/COLLABORATOR) quase sempre viram PR e usam vocabulário interno; o TF-IDF aprende "quem escreveu". Por isso cada repositório tem também o recorte só com autores de fora, que é o público da fila de triagem. Os modelos são treinados com todos; só a avaliação é recortada.
- O TypeScript tem poucas issues no teste; o intervalo de confiança mostra a incerteza.
- O backfill usa o texto atual de issues já fechadas (limitação registrada no contrato), igual para todos os métodos.
- O corte do TF-IDF e da heurística com pesos vem de previsões de validação cruzada no treino; o `C` do TF-IDF foi escolhido no mesmo treino, o que deixa o corte levemente otimista.
