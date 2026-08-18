# Prompt — Seção 4.10: mudanças significativas

## Configuração

- `PASTA_CSV`: `C:\Users\admin\Desktop\Advanced\Relatorio foda\outputs\2026\2026-07-27`
- `ARQUIVO_SAIDA`: `C:\Users\admin\Desktop\Advanced\Relatorio foda\outputs\2026\2026-07-27\generativos\04_10_mudancas_significativas.md`
- `PDF_REFERENCIA_EDITORIAL`: `C:\Users\admin\Downloads\Rel. Desempenho Jul 27-31.pdf`

## Tarefa

Leia os CSVs semanais de `PASTA_CSV`, em especial `04_conversao_responsavel.csv`, `05_movimentacao_semanal.csv`, `07_novos_leads_semana.csv`, `08_etapas_por_consultor.csv`, `09_tempo_medio_resposta.csv` e `11_composicao_leads_perdidos.csv`.

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

## Regra de gravação

Grave somente o Markdown final em `ARQUIVO_SAIDA`. Se já existir, sobrescreva integralmente. Não crie arquivos duplicados, numerados ou com timestamps.
