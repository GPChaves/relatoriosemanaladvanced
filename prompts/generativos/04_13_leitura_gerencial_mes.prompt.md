# Prompt — Seção 4.13: leitura gerencial do mês

## Configuração

- `PASTA_CSV`: fornecida no envelope da tarefa.
- `ARQUIVO_SAIDA`: fornecido no envelope da tarefa.
- `PDF_REFERENCIA_EDITORIAL`: opcional; use somente quando o envelope fornecer um arquivo existente.

## Tarefa

Verifique em `01_identificacao_periodo.csv` se a semana fecha o mês. Se não fechar, produza apenas uma nota objetiva de não aplicabilidade.

Quando aplicável, leia `02_distribuicao_mensal_responsavel.csv`, `03_numeros_globais_etapas.csv`, `13_analise_quantitativa_mes.csv` e `14_resumo_consolidado_mes.csv` e produza `## Análise completa do mês — leitura gerencial`.

Escreva como uma análise autoral do gestor. No texto entregue, não mencione arquivos, CSVs, prompts, agentes, inteligência artificial, automação, scripts, APIs nem se algum dado foi fornecido manualmente. Use os bastidores técnicos apenas para apurar os fatos.

Os arquivos `02` e `03` usam a última transição terminal de cada lead no mês para **Serviço iniciado** ou **Perdido**. Os arquivos `13` e `14` acompanham os leads **criados** no mês e seu estado atual. Não tente fazer os totais desses dois universos coincidirem e explique a diferença quando ela for relevante. A atribuição por consultor usa somente `responsible_user_id`.

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

## Público e linguagem

- Escreva para donos de oficina mecânica, sem presumir conhecimento de análise de dados.
- Use frases curtas, voz direta e termos comuns do dia a dia.
- Prefira “leads que entraram” a “coorte”, “conferir” a “reconciliar” e “parte/percentual” a “participação relativa”.
- Ao citar pontos percentuais, explique a mudança com os números antes e depois.
- Evite linguagem corporativa e expressões abstratas, como “materialmente relevante”, “distribuição operacional”, “causalidade” e “evidência adicional”. Se um termo técnico for indispensável, explique-o na mesma frase.
- Corte repetições e resuma ideias longas, sem retirar números importantes, limites dos dados, hipóteses ou ações práticas.
- Prefira uma tabela Markdown compacta para tendências mensais e use a prosa apenas para as conclusões prioritárias.

## Regra de gravação

Grave somente o Markdown final no caminho exato de `ARQUIVO_SAIDA`. Sobrescreva qualquer conteúdo anterior e não gere arquivo alternativo.
