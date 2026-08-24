# Prompt — Seção 4.17: diferenças entre consultores

## Configuração

- `PASTA_CSV`: fornecida no envelope da tarefa.
- `ARQUIVO_SAIDA`: fornecido no envelope da tarefa.
- `PDF_REFERENCIA_EDITORIAL`: opcional; use somente quando o envelope fornecer um arquivo existente.

## Tarefa

Leia `04_conversao_responsavel.csv`, `05_movimentacao_semanal.csv`, `06_nota_metodologica_movimentacao.csv`, `07_novos_leads_semana.csv`, `08_etapas_por_consultor.csv` e `09_tempo_medio_resposta.csv` em `PASTA_CSV`.

Use cada base com seu significado: conversão e etapas representam leads que chegaram a **Serviço iniciado** ou **Perdido** no período; novos leads representam criações; movimentação representa eventos. Não some nem confronte diretamente esses volumes como se fossem o mesmo universo. Para atribuição entre consultores, considere exclusivamente o campo personalizado **Usuário responsável**.

Produza `## Diferenças observadas entre os consultores`.

Compare somente diferenças quantitativas sustentadas pelos dados: volume recebido, participação nos novos leads, movimentação, conversão e composição atual das etapas. Para cada diferença relevante:

- informe a base numérica;
- explique uma ou mais hipóteses plausíveis;
- diga qual evidência adicional seria necessária para confirmar a interpretação;
- não confunda usuário que movimentou o CRM com pessoa que conduziu a negociação;
- não crie ranking qualitativo;
- não atribua estilo, conhecimento técnico, proatividade ou qualidade de comunicação sem amostra de conversas;
- trate o tamanho desigual das carteiras e a maturação como limitações.

Use subtítulos curtos e encerre com `### O que acompanhar`, contendo métricas ou verificações para as próximas semanas.

Use o PDF apenas como referência de tom. Não reutilize seus casos ou números.

+## Público e linguagem

- Escreva para donos de oficina mecânica, sem presumir conhecimento de análise de dados.
- Use frases curtas, voz direta e termos comuns do dia a dia.
- Prefira “leads que entraram” a “coorte”, “conferir” a “reconciliar” e “parte/percentual” a “participação relativa”.
- Ao citar pontos percentuais, explique a mudança com os números antes e depois.
- Evite linguagem corporativa e expressões abstratas, como “materialmente relevante”, “distribuição operacional”, “causalidade” e “evidência adicional”. Se um termo técnico for indispensável, explique-o na mesma frase.
- Corte repetições e resuma ideias longas, sem retirar números importantes, limites dos dados, hipóteses ou ações práticas.

## Regra de gravação

Grave somente o Markdown final em `ARQUIVO_SAIDA`, sobrescrevendo o existente. Não gere duplicatas, versões ou timestamps.
