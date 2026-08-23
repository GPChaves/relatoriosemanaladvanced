# Prompt — Seção 4.15: auditoria de uso do CRM

## Configuração

- `PASTA_CSV`: fornecida no envelope da tarefa.
- `ARQUIVO_SAIDA`: fornecido no envelope da tarefa.
- `PDF_REFERENCIA_EDITORIAL`: opcional; use somente quando o envelope fornecer um arquivo existente.

## Tarefa

Leia `05_movimentacao_semanal.csv`, `06_nota_metodologica_movimentacao.csv`, `08_etapas_por_consultor.csv` e `11_composicao_leads_perdidos.csv` em `PASTA_CSV`.

Produza `## Auditoria de uso do CRM` somente até o nível sustentado pelos dados agregados.

Procure sinais quantitativos de qualidade de cadastro ou operação, como:

- perdas sem motivo ou com motivo genérico;
- proporção relevante de eventos sem usuário atribuído;
- diferenças entre movimentação e responsabilidade que exijam investigação;
- concentração inesperada em etapas ou motivos de perda.

Não afirme que um lead específico foi classificado incorretamente sem registro individual ou conversa que comprove isso. Não invente exemplos, capturas, IDs ou falas. Quando os CSVs permitirem apenas levantar um risco, use a formulação `sinal para auditoria`, nunca `erro confirmado`.

Estruture em:

- `### Sinais encontrados`
- `### Verificações recomendadas`
- `### Evidências necessárias para confirmar`

O PDF serve apenas como referência do tipo de auditoria desejada. Os casos pessoais e números do PDF não podem ser reutilizados.

+## Público e linguagem

- Escreva para donos de oficina mecânica, sem presumir conhecimento de análise de dados.
- Use frases curtas, voz direta e termos comuns do dia a dia.
- Prefira “leads que entraram” a “coorte”, “conferir” a “reconciliar” e “parte/percentual” a “participação relativa”.
- Ao citar pontos percentuais, explique a mudança com os números antes e depois.
- Evite linguagem corporativa e expressões abstratas, como “materialmente relevante”, “distribuição operacional”, “causalidade” e “evidência adicional”. Se um termo técnico for indispensável, explique-o na mesma frase.
- Corte repetições e resuma ideias longas, sem retirar números importantes, limites dos dados, hipóteses ou ações práticas.

## Regra de gravação

Grave somente o Markdown final em `ARQUIVO_SAIDA`. Sobrescreva o arquivo existente e não crie duplicatas ou versões paralelas.
