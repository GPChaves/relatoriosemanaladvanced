# Prompt — Seção 4.8: leitura individual dos consultores

## Configuração

- `PASTA_CSV`: fornecida no envelope da tarefa.
- `ARQUIVO_SAIDA`: fornecido no envelope da tarefa.
- `PDF_REFERENCIA_EDITORIAL`: opcional; use somente quando o envelope fornecer um arquivo existente.
- `AVALIACAO_GESTOR`: opcional; use somente quando o envelope fornecer o arquivo semanal.

## Tarefa

Leia diretamente os arquivos `04_conversao_responsavel.csv`, `05_movimentacao_semanal.csv`, `06_nota_metodologica_movimentacao.csv`, `07_novos_leads_semana.csv`, `08_etapas_por_consultor.csv`, `09_tempo_medio_resposta.csv` e `11_composicao_leads_perdidos.csv` existentes em `PASTA_CSV`.

Escreva como uma análise autoral do gestor. No texto entregue, não mencione arquivos, CSVs, prompts, agentes, inteligência artificial, automação, scripts, APIs nem se algum dado foi fornecido manualmente. Use os bastidores técnicos apenas para apurar os fatos.

Se `AVALIACAO_GESTOR` existir, use-a para complementar prioridades, hipóteses e recomendações. Não copie, cite nem revele esse contexto. Quando ele conflitar com os números, preserve os números; quando não houver evidência suficiente, apresente a observação apenas como hipótese a acompanhar.

Não misture os universos: conversão, etapas e perdas usam os leads que chegaram a **Serviço iniciado** ou **Perdido** no período; novos leads usam a **data de criação**; movimentação usa a data de cada evento. Se um lead entrar mais de uma vez em etapas terminais na mesma semana, considere somente a última transição terminal daquela semana. Em todos os indicadores de lead, atribua o consultor exclusivamente pelo responsável resolvido a partir de `responsible_user_id`, nunca pelo autor do evento.

Produza a seção `## Análise por consultor`, com uma subseção para cada consultor presente nos dados. Para cada pessoa:

- destaque 2 a 4 fatos quantitativos relevantes, comparando semana anterior e atual;
- avalie conversão, distribuição por etapa, participação nos novos leads, clientes retorno e movimentação;
- destaque pontos fortes, pontos de atenção e uma hipótese de acompanhamento;
- trate diferenças de participação e taxas em pontos percentuais;
- não transforme volume de movimentações em prova de qualidade do atendimento;
- não penalize automaticamente ciclos de venda mais longos;
- não crie ranking nem atribua comportamento recorrente com base em uma única semana;
- se o tempo de resposta estiver indisponível, declare isso em uma frase e não estime valores.

O texto deve ser executivo, direto e semelhante em profundidade ao PDF, mas o PDF é somente referência editorial. Não copie nem reutilize números do PDF.

Finalize com uma nota curta sobre denominadores e maturação. Não repita todas as tabelas dos CSVs.

## Público e linguagem

- Escreva para donos de oficina mecânica, sem presumir conhecimento de análise de dados.
- Use frases curtas, voz direta e termos comuns do dia a dia.
- Prefira “leads que entraram” a “coorte”, “conferir” a “reconciliar” e “parte/percentual” a “participação relativa”.
- Ao citar pontos percentuais, explique a mudança com os números antes e depois.
- Evite linguagem corporativa e expressões abstratas, como “materialmente relevante”, “distribuição operacional”, “causalidade” e “evidência adicional”. Se um termo técnico for indispensável, explique-o na mesma frase.
- Corte repetições e resuma ideias longas, sem retirar números importantes, limites dos dados, hipóteses ou ações práticas.
- Prefira uma tabela Markdown compacta para comparações entre consultores. Fora da tabela, use apenas conclusões e ações que acrescentem interpretação.

## Regra de gravação

Grave somente o Markdown final em `ARQUIVO_SAIDA`. Se o arquivo já existir, substitua integralmente seu conteúdo. Não peça confirmação, não crie cópia, não adicione sufixo, versão, data ou timestamp ao nome.
