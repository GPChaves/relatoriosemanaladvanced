# Prompt — Seção 4.18: limitações e próximos passos

## Configuração

- `PASTA_CSV`: fornecida no envelope da tarefa.
- `ARQUIVO_SAIDA`: fornecido no envelope da tarefa.
- `PDF_REFERENCIA_EDITORIAL`: opcional; use somente quando o envelope fornecer um arquivo existente.

## Tarefa

Leia todos os CSVs de `PASTA_CSV` e produza `## Limitações e próximos passos`.

Escreva como uma análise autoral do gestor. No texto entregue, não mencione arquivos, CSVs, prompts, agentes, inteligência artificial, automação, scripts, APIs nem se algum dado foi fornecido manualmente. Use os bastidores técnicos apenas para apurar os fatos.

Identifique somente limitações que realmente se aplicam, incluindo quando pertinente:

- maturação incompleta dos leads mais recentes;
- segmentos semanais parciais dentro do mês;
- ausência de histórico de outros meses;
- metodologia de movimentação baseada em pares usuário-lead e eventos;
- eventos sem usuário e exclusões metodológicas;
- tempo de resposta indisponível;
- falta de conteúdo de conversas para análise qualitativa;
- dados agregados insuficientes para confirmar causalidade ou erros individuais de CRM.

Para cada limitação, associe um próximo passo verificável. Priorize de 4 a 7 ações, indicando o que medir, qual fonte obter ou qual rotina implantar. Evite recomendações genéricas.

Estruture em:

- `### Limitações que afetam a leitura`
- `### Próximos passos priorizados`

O PDF é somente referência editorial. Não copie seus casos, números ou afirmações.

+## Público e linguagem

- Escreva para donos de oficina mecânica, sem presumir conhecimento de análise de dados.
- Use frases curtas, voz direta e termos comuns do dia a dia.
- Prefira “leads que entraram” a “coorte”, “conferir” a “reconciliar” e “parte/percentual” a “participação relativa”.
- Ao citar pontos percentuais, explique a mudança com os números antes e depois.
- Evite linguagem corporativa e expressões abstratas, como “materialmente relevante”, “distribuição operacional”, “causalidade” e “evidência adicional”. Se um termo técnico for indispensável, explique-o na mesma frase.
- Corte repetições e resuma ideias longas, sem retirar números importantes, limites dos dados, hipóteses ou ações práticas.

## Regra de gravação

Grave somente o Markdown final no caminho exato de `ARQUIVO_SAIDA`. Substitua integralmente qualquer arquivo anterior e não crie cópias, sufixos ou versões.
