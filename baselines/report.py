"""Relatório em Markdown dos baselines."""
from .metrics import TARGET_PRECISION
from .models import MODELS

REPO_NAMES = {"all": "Todos (3 principais)"}


def _pct(x):
    return "—" if x is None else f"{100 * x:.0f}%"


def _num(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def markdown(results, repos, generated_at):
    lines = [f"# Baselines da Fase 1 ({generated_at[:10]})", "",
             "Gerado por `python -m baselines` a partir do branch `data` (gabarito `gab-1`, Jev `q1`/`clean-1`).",
             "Positivo = fechada **sem ação**. Corte temporal por repositório: 70% mais antigas (por `created_at`) "
             "para treino, 30% mais recentes para teste. Todo ajuste usa só o treino.", "",
             f"Precisão, recall e cobertura usam o corte escolhido no treino para precisão ≥ {TARGET_PRECISION:.0%} "
             "em \"sem ação\" (a precisão-alvo da proposta) e aplicado ao teste; \"—\" = o treino não atinge o alvo.", ""]
    for repo in [*repos, "all"]:
        any_r = results[(repo, next(iter(MODELS)))]
        lines += [f"## {REPO_NAMES.get(repo, repo)}", "",
                  f"Treino {any_r['n_train']} ({any_r['train_period'][0]} a {any_r['train_period'][1]}) · "
                  f"teste {any_r['n']} ({any_r['test_period'][0]} a {any_r['test_period'][1]}) · "
                  f"sem ação no teste: {_pct(any_r['base_rate'])}", "",
                  "| Modelo | AUC [IC 95%] | Precisão média | Brier | Precisão @corte | Recall @corte | Cobertura |",
                  "|---|---|---|---|---|---|---|"]
        for key, (name, _) in MODELS.items():
            r = results[(repo, key)]
            lines.append(f"| {name} | {r['auc']:.3f} [{r['auc_ci'][0]:.3f}–{r['auc_ci'][1]:.3f}] | "
                         f"{r['average_precision']:.3f} | {_num(r['brier'])} | {_pct(r['precision_no_action'])} | "
                         f"{_pct(r['recall_no_action'])} | {_pct(r['coverage'])} |")
        ext = results[(repo, next(iter(MODELS)))].get("external")
        if ext:
            lines += ["", f"Só autores de fora da equipe (sem OWNER/MEMBER/COLLABORATOR): {ext['n']} issues no teste, "
                      f"sem ação: {_pct(ext['base_rate'])}. Mesmos modelos e cortes.", "",
                      "| Modelo | AUC [IC 95%] | Precisão média | Precisão @corte | Recall @corte | Cobertura |",
                      "|---|---|---|---|---|---|"]
            for key, (name, _) in MODELS.items():
                e = results[(repo, key)]["external"]
                lines.append(f"| {name} | {e['auc']:.3f} [{e['auc_ci'][0]:.3f}–{e['auc_ci'][1]:.3f}] | "
                             f"{e['average_precision']:.3f} | {_pct(e['precision_no_action'])} | "
                             f"{_pct(e['recall_no_action'])} | {_pct(e['coverage'])} |")
        notes = [f"{MODELS[k][0]}: {results[(repo, k)]['note']}" for k in MODELS if results[(repo, k)]["note"]]
        lines += ["", "Notas: " + "; ".join(notes) + ".", ""]
    lines += ["## Como ler", "",
              "- **AUC**: chance de o modelo dar nota maior a uma \"sem ação\" do que a uma \"com ação\" sorteadas; 0,5 = acaso.",
              "- **Precisão média**: área sob a curva precisão × recall; compare com a taxa-base de \"sem ação\" do teste.",
              "- **Brier**: erro quadrático das probabilidades (menor é melhor); só para modelos que dão probabilidade.",
              "- **Jev + regressão logística** é uma referência do que um calibrador simples faria com as 5 respostas, "
              "não o calibrador do Back.", "",
              "## Limitações", "",
              "- No VS Code, relatórios gerados pelo próprio editor (tabelas \"System Info\", lista de extensões) aparecem "
              "mais entre as \"sem ação\". O TF-IDF pode estar aprendendo esse formato, não o conteúdo; a limpeza `clean-1` "
              "não remove essas tabelas.",
              "- Issues abertas pela própria equipe (OWNER/MEMBER/COLLABORATOR) quase sempre viram PR e usam vocabulário "
              "interno; o TF-IDF aprende \"quem escreveu\". Por isso cada repositório tem também o recorte só com autores de "
              "fora, que é o público da fila de triagem. Os modelos são treinados com todos; só a avaliação é recortada.",
              "- O TypeScript tem poucas issues no teste; o intervalo de confiança mostra a incerteza.",
              "- O backfill usa o texto atual de issues já fechadas (limitação registrada no contrato), igual para todos os métodos.",
              "- O corte do TF-IDF e da heurística com pesos vem de previsões de validação cruzada no treino; o `C` do TF-IDF "
              "foi escolhido no mesmo treino, o que deixa o corte levemente otimista.", ""]
    return "\n".join(lines)
