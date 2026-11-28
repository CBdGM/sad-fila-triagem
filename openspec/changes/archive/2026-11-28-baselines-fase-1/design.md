## Context

Dados: `predictions.jsonl` com `mode: backfill` (texto limpo `clean-1` que o Jev recebeu, já com credenciais redigidas) e `outcomes.jsonl` (gabarito `gab-1`). Proporção de "sem ação" muito diferente entre repositórios: ~68% VS Code, ~48% TypeScript, ~39% Godot.

## Goals / Non-Goals

**Goals:** comparação justa, reprodutível e sem vazamento entre baselines baratos e o sinal do Jev, por repositório e no conjunto.

**Non-Goals:** o calibrador oficial e os cortes das faixas (Back); Laya e LLM forte (custo, dependências); otimizar a heurística para estes dados.

## Decisions

**Rótulo.** Positivo = `no_action`, negativo = `action`, pelo desfecho mais recente da issue, só se corresponde ao `closed_at` atual; `excluded` fica fora, como na Fase 0.

**Texto.** O mesmo `input_text` que o Jev recebeu, para comparar sinais sobre a mesma entrada. Previsões `daily` (de abertas) não entram.

**Corte temporal por repositório.** Ordena por `created_at` e usa as 70% mais antigas para treino e as 30% mais recentes para teste, como no desenho "temporal" da proposta. Evita que o modelo veja o futuro e mantém a proporção de cada repositório nos dois lados. O conjunto "todos" junta os treinos e os testes de cada repositório.

**Heurística definida antes de medir.** Sinais clássicos de triagem, sem ajuste a estes dados: tamanho do texto (log das palavras), texto curto (< 30 palavras), stack trace ou mensagem de erro, bloco de código, passos numerados, versão informada (`x.y.z`), pergunta de uso ("how do I", "is there a way"…), imagem e link. Duas versões: **regras fixas** (soma com sinais escolhidos a priori: curto e pergunta somam; stack trace, código, passos e versão subtraem; sem treino) e **pesos aprendidos** (regressão logística padronizada sobre os mesmos sinais).

**TF-IDF + regressão logística.** Palavras e bigramas, `sublinear_tf`, `min_df=3`, `max_df=0.9`, até 100 mil termos; regularização `C` escolhida por validação cruzada estratificada de 5 dobras **só no treino**, maximizando AUC. Semente fixa.

**Referências do Jev.** "Jev bruto": `1 − is_defect`, sem treino. "Jev + regressão": regressão logística sobre as 5 respostas (4 probabilidades e a severidade esperada), que é o que um calibrador simples faria; não é o calibrador do Back.

**Métricas.** AUC com IC de 95% por bootstrap (1.000 reamostras do teste), precisão média (PR-AUC), taxa-base e Brier (só para quem dá probabilidade). Para precisão, recall e cobertura, o corte é escolhido nas previsões de validação cruzada do treino como o menor limiar com precisão ≥ 0,90 (a precisão-alvo da proposta para a faixa "provavelmente sem ação") e aplicado ao teste; se o treino não atinge 0,90, as três ficam nulas. Cobertura = fração do teste que cai acima do corte.

**Saída.** `docs/resultados/baselines-<data>.md` (tabela e notas) e `baselines-<data>.json` com um documento no formato do `metrics.schema.json` (`design: temporal`, uma avaliação por modelo e repositório), validado pelo contrato.

## Risks / Trade-offs

- [Atalho de formato] → relatórios automáticos do VS Code (tabelas "System Info") aparecem mais entre "sem ação"; o TF-IDF pode aprender o formato, não o conteúdo. Registrado no relatório; a limpeza `clean-1` não remove essas tabelas.
- [TypeScript pequeno] → ~140 issues no teste; o IC mostra a incerteza.
- [Backfill usa o texto atual de issues já fechadas] → limitação já registrada no contrato; vale igualmente para todos os métodos.
