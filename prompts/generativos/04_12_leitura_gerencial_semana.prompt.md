# Prompt — Seção 4.12: leitura gerencial da semana

## Configuração

- `PASTA_CSV`: fornecida no envelope da tarefa.
- `ARQUIVO_SAIDA`: fornecido no envelope da tarefa.
- `PDF_REFERENCIA_EDITORIAL`: opcional; use somente quando o envelope fornecer um arquivo existente.

## Tarefa

Leia todos os CSVs de `PASTA_CSV` e produza `## Leitura gerencial da semana`.

Escreva como uma análise autoral do gestor. No texto entregue, não mencione arquivos, CSVs, prompts, agentes, inteligência artificial, automação, scripts, APIs nem se algum dado foi fornecido manualmente. Use os bastidores técnicos apenas para apurar os fatos.

Distinga claramente três bases: leads que chegaram a **Serviço iniciado** ou **Perdido** no período (conversão, etapas e perdas), leads **criados** no período (novos leads) e eventos ocorridos no período (movimentação). Não trate diferenças entre essas bases como inconsistência automática. A atribuição dos indicadores de lead usa somente o campo personalizado **Usuário responsável**.

Escolha de 3 a 5 insights realmente acionáveis. Para cada insight:

1. comece com uma frase em negrito que declare o fato principal;
2. apresente os números essenciais e a base de comparação;
3. explique o possível significado, deixando claro quando for hipótese;
4. registre a limitação que pode alterar a interpretação;
5. recomende uma verificação, correção ou acompanhamento concreto.

Priorize mudanças em volume de novos leads, conversão, distribuição entre consultores, movimentação, etapas e composição das perdas. Não repita todas as tabelas. Não atribua automaticamente variações do CRM a campanhas, site, WhatsApp ou desempenho individual. Quando uma causa depender de fonte externa, diga exatamente o que deve ser verificado.

Use o PDF somente para calibrar tom e profundidade. Os fatos e números devem vir exclusivamente dos CSVs. Se uma métrica estiver indisponível, não estime.

Finalize com `### Ações recomendadas`, contendo uma lista curta, priorizada e verificável.

+## Público e linguagem

- Escreva para donos de oficina mecânica, sem presumir conhecimento de análise de dados.
- Use frases curtas, voz direta e termos comuns do dia a dia.
- Prefira “leads que entraram” a “coorte”, “conferir” a “reconciliar” e “parte/percentual” a “participação relativa”.
- Ao citar pontos percentuais, explique a mudança com os números antes e depois.
- Evite linguagem corporativa e expressões abstratas, como “materialmente relevante”, “distribuição operacional”, “causalidade” e “evidência adicional”. Se um termo técnico for indispensável, explique-o na mesma frase.
- Corte repetições e resuma ideias longas, sem retirar números importantes, limites dos dados, hipóteses ou ações práticas.

## Regra de gravação

Grave somente o Markdown final em `ARQUIVO_SAIDA`, substituindo qualquer versão existente. Não crie cópias, sufixos ou arquivos adicionais.
