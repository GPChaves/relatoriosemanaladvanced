# Prompt — Seção 4.16: amostragem qualitativa dos atendimentos

## Configuração

- `PASTA_CSV`: fornecida no envelope da tarefa.
- `ARQUIVO_SAIDA`: fornecido no envelope da tarefa.
- `PDF_REFERENCIA_EDITORIAL`: opcional; use somente quando o envelope fornecer um arquivo existente.

## Tarefa

Antes de qualquer outra ação, procure estas três análises individuais:

- `PASTA_CSV/generativos/atendimentos/01_analise.md`
- `PASTA_CSV/generativos/atendimentos/02_analise.md`
- `PASTA_CSV/generativos/atendimentos/03_analise.md`

Se as três existirem, elas já foram produzidas por agentes independentes, um por fonte de atendimento. Nesse caso, não volte a analisar os atendimentos e não acrescente interpretações. Apenas reúna o conteúdo, nesta ordem, sob o título `## Amostragem qualitativa dos atendimentos`, mantendo os blocos `### Atendimento 1`, `### Atendimento 2` e `### Atendimento 3`. Abra a seção com uma frase curta avisando que três casos são uma amostra e não representam todos os atendimentos. Essa consolidação deve substituir `ARQUIVO_SAIDA` e nunca substituir os três arquivos individuais.

Se apenas uma ou duas análises individuais existirem, não produza uma consolidação parcial. Informe que faltam análises e preserve os arquivos individuais existentes.

Use as regras abaixo somente quando a pasta de análises individuais não existir, para manter compatibilidade com semanas antigas.

Verifique os arquivos disponíveis em `PASTA_CSV`. Uma análise qualitativa só pode ser produzida se existir uma fonte específica de amostragem com conteúdo anonimizado de conversas ou avaliações individuais documentadas.

Os CSVs agregados de métricas não bastam para avaliar clareza da comunicação, domínio técnico, tratamento de objeções, defesa de preço, pressão comercial ou qualidade de follow-up.

Se não houver fonte qualitativa adequada, produza:

`## Amostragem qualitativa dos atendimentos`

seguida de uma nota curta explicando que a seção está indisponível, o dado faltante e o formato mínimo necessário para habilitá-la no futuro. Inclua uma lista dos campos mínimos: identificador interno anonimizado, consultor, resultado, contexto resumido, timestamps, mensagens anonimizadas e classificação no CRM.

Se houver fonte adequada, analise somente os casos fornecidos, anonimize dados pessoais, descreva pontos positivos e oportunidades por caso e trate a amostra como indício, não como regra geral.

Não reutilize casos, nomes, telefones, IDs, falas ou conclusões do PDF. O PDF é apenas referência editorial.

+## Público e linguagem

- Escreva para donos de oficina mecânica, sem presumir conhecimento de análise de dados.
- Use frases curtas, voz direta e termos comuns do dia a dia.
- Prefira “leads que entraram” a “coorte”, “conferir” a “reconciliar” e “parte/percentual” a “participação relativa”.
- Ao citar pontos percentuais, explique a mudança com os números antes e depois.
- Evite linguagem corporativa e expressões abstratas, como “materialmente relevante”, “distribuição operacional”, “causalidade” e “evidência adicional”. Se um termo técnico for indispensável, explique-o na mesma frase.
- Corte repetições e resuma ideias longas, sem retirar números importantes, limites dos dados, hipóteses ou ações práticas.

## Regra de gravação

Grave somente o Markdown final em `ARQUIVO_SAIDA`, substituindo qualquer versão anterior. Não crie cópias ou arquivos com sufixo.
