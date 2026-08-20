# Prompt — Seção 4.8: leitura individual dos consultores

## Configuração

- `PASTA_CSV`: `C:\Users\admin\Desktop\Advanced\Relatorio foda\outputs\2026\2026-07-27`
- `ARQUIVO_SAIDA`: `C:\Users\admin\Desktop\Advanced\Relatorio foda\outputs\2026\2026-07-27\generativos\04_08_leitura_consultores.md`
- `PDF_REFERENCIA_EDITORIAL`: `C:\Users\admin\Downloads\Rel. Desempenho Jul 27-31.pdf`

## Tarefa

Leia diretamente os arquivos `04_conversao_responsavel.csv`, `05_movimentacao_semanal.csv`, `06_nota_metodologica_movimentacao.csv`, `07_novos_leads_semana.csv`, `08_etapas_por_consultor.csv`, `09_tempo_medio_resposta.csv` e `11_composicao_leads_perdidos.csv` existentes em `PASTA_CSV`.

Produza a seção `## Análise por consultor`, com uma subseção para cada consultor presente nos dados. Para cada pessoa:

- destaque 2 a 4 fatos quantitativos relevantes, comparando semana anterior e atual;
- avalie conversão, distribuição por etapa, participação nos novos leads e movimentação;
- destaque pontos fortes, pontos de atenção e uma hipótese de acompanhamento;
- trate diferenças de participação e taxas em pontos percentuais;
- não transforme volume de movimentações em prova de qualidade do atendimento;
- não penalize automaticamente ciclos de venda mais longos;
- não crie ranking nem atribua comportamento recorrente com base em uma única semana;
- se o tempo de resposta estiver indisponível, declare isso em uma frase e não estime valores.

O texto deve ser executivo, direto e semelhante em profundidade ao PDF, mas o PDF é somente referência editorial. Não copie nem reutilize números do PDF.

Finalize com uma nota curta sobre denominadores e maturação. Não repita todas as tabelas dos CSVs.

+## Público e linguagem

- Escreva para donos de oficina mecânica, sem presumir conhecimento de análise de dados.
- Use frases curtas, voz direta e termos comuns do dia a dia.
- Prefira “leads que entraram” a “coorte”, “conferir” a “reconciliar” e “parte/percentual” a “participação relativa”.
- Ao citar pontos percentuais, explique a mudança com os números antes e depois.
- Evite linguagem corporativa e expressões abstratas, como “materialmente relevante”, “distribuição operacional”, “causalidade” e “evidência adicional”. Se um termo técnico for indispensável, explique-o na mesma frase.
- Corte repetições e resuma ideias longas, sem retirar números importantes, limites dos dados, hipóteses ou ações práticas.

## Regra de gravação

Grave somente o Markdown final em `ARQUIVO_SAIDA`. Se o arquivo já existir, substitua integralmente seu conteúdo. Não peça confirmação, não crie cópia, não adicione sufixo, versão, data ou timestamp ao nome.
