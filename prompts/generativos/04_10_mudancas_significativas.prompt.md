# Prompt — Seção 4.10: mudanças significativas

## Configuração

- `PASTA_CSV`: fornecida no envelope da tarefa.
- `ARQUIVO_SAIDA`: fornecido no envelope da tarefa.
- `PDF_REFERENCIA_EDITORIAL`: opcional; use somente quando o envelope fornecer um arquivo existente.

## Tarefa

Leia os CSVs semanais de `PASTA_CSV`, em especial `04_conversao_responsavel.csv`, `05_movimentacao_semanal.csv`, `07_novos_leads_semana.csv`, `08_etapas_por_consultor.csv`, `09_tempo_medio_resposta.csv` e `11_composicao_leads_perdidos.csv`.

Escreva como uma análise autoral do gestor. No texto entregue, não mencione arquivos, CSVs, prompts, agentes, inteligência artificial, automação, scripts, APIs nem se algum dado foi fornecido manualmente. Use os bastidores técnicos apenas para apurar os fatos.

Respeite os universos informados nos CSVs: conversão, etapas e perdas usam a chegada a **Serviço iniciado** ou **Perdido**; novos leads usam a **criação**; movimentação usa os eventos. Não compare esses volumes como se medissem a mesma população. O consultor dos indicadores de lead vem exclusivamente do campo personalizado **Usuário responsável**.

Produza `## Mudanças significativas entre as duas últimas semanas`.

Selecione somente mudanças materialmente relevantes. Use como critérios a magnitude absoluta, a variação em pontos percentuais, a importância operacional e a utilidade gerencial. Não inclua um indicador apenas porque existe no relatório.

Apresente uma tabela Markdown com as colunas:

| Indicador | Semana anterior | Semana atual | Variação | Por que merece atenção |

Regras:

- volumes: variação absoluta, nunca pontos percentuais;
- taxas e participações: variação em pontos percentuais;
- tempo: variação em minutos, somente se disponível;
- não misture o valor atual e a variação na mesma célula;
- depois da tabela, escreva um parágrafo curto conectando as mudanças sem afirmar causalidade;
- se a semana for parcial ou tiver maturação incompleta, destaque a ressalva;
- não use o PDF como fonte de valores.

+## Público e linguagem

- Escreva para donos de oficina mecânica, sem presumir conhecimento de análise de dados.
- Use frases curtas, voz direta e termos comuns do dia a dia.
- Prefira “leads que entraram” a “coorte”, “conferir” a “reconciliar” e “parte/percentual” a “participação relativa”.
- Ao citar pontos percentuais, explique a mudança com os números antes e depois.
- Evite linguagem corporativa e expressões abstratas, como “materialmente relevante”, “distribuição operacional”, “causalidade” e “evidência adicional”. Se um termo técnico for indispensável, explique-o na mesma frase.
- Corte repetições e resuma ideias longas, sem retirar números importantes, limites dos dados, hipóteses ou ações práticas.

## Regra de gravação

Grave somente o Markdown final em `ARQUIVO_SAIDA`. Se já existir, sobrescreva integralmente. Não crie arquivos duplicados, numerados ou com timestamps.
