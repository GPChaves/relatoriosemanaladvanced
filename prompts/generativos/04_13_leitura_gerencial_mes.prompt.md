# Prompt — Seção 4.13: leitura gerencial do mês

## Configuração

- `PASTA_CSV`: `C:\Users\admin\Desktop\Advanced\Relatorio foda\outputs\2026\2026-07-27`
- `ARQUIVO_SAIDA`: `C:\Users\admin\Desktop\Advanced\Relatorio foda\outputs\2026\2026-07-27\generativos\04_13_leitura_gerencial_mes.md`
- `PDF_REFERENCIA_EDITORIAL`: `C:\Users\admin\Downloads\Rel. Desempenho Jul 27-31.pdf`

## Tarefa

Verifique em `01_identificacao_periodo.csv` se a semana fecha o mês. Se não fechar, produza apenas uma nota objetiva de não aplicabilidade.

Quando aplicável, leia `02_distribuicao_mensal_responsavel.csv`, `03_numeros_globais_etapas.csv`, `13_analise_quantitativa_mes.csv` e `14_resumo_consolidado_mes.csv` e produza `## Análise completa do mês — leitura gerencial`.

O texto deve:

- abrir com 2 a 4 conclusões executivas em lista;
- identificar maior e menor volume semanal;
- comparar desempenho apenas quando as semanas forem comparáveis;
- destacar melhor e pior taxa entre semanas amadurecidas, respeitando as marcações de semana parcial;
- comentar serviços iniciados, agendados, perdidos e em andamento;
- informar o consolidado mensal sem reconstruir toda a tabela;
- mencionar distribuição mensal por responsável somente quando ela trouxer implicação útil;
- distinguir quantidade, taxa e variação em pontos percentuais;
- tratar a última semana com cautela por maturação, mesmo quando o período calendário já estiver completo;
- reconhecer a ausência de histórico de outros meses para conclusões de sazonalidade.

O PDF é referência editorial, não fonte numérica. Use somente os CSVs atuais.

Finalize com `### Implicações para o próximo mês`, contendo ações de acompanhamento sustentadas pelos dados.

## Regra de gravação

Grave somente o Markdown final no caminho exato de `ARQUIVO_SAIDA`. Sobrescreva qualquer conteúdo anterior e não gere arquivo alternativo.
