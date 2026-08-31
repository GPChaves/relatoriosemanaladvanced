# Subagentes generativos

Use esta referência depois que todos os CSVs quantitativos da semana forem validados.

## Isolamento

Crie cada agente com `fork_turns="none"`. O envelope deve conter somente:

- o objetivo de escrever um único arquivo;
- o caminho absoluto do prompt;
- os caminhos absolutos das fontes declaradas no manifesto;
- o caminho absoluto e exclusivo da saída;
- a instrução de não ler outras semanas nem outras fontes.
- a instrução de escrever como análise autoral do gestor, sem expor arquivos internos, coleta manual, agentes, IA, automação, scripts ou APIs.

Agentes não devem compartilhar uma saída. Execute em ondas compatíveis com os slots disponíveis e espere a conclusão de toda onda antes de validar seus arquivos.

Peça textos enxutos: tabelas Markdown devem substituir enumerações repetitivas sempre que os dados forem comparáveis; a prosa deve se limitar às conclusões e ações que a tabela não comunica sozinha.

## Atendimentos

Prepare primeiro os três caminhos e hashes com `processar_atendimentos.py`.

Crie três agentes isolados. Cada um recebe somente o prompt individual, uma fonte, `cliente_nome`, `lead_id` e seu caminho `generativos/atendimentos/0N_analise.md`. Para `type=image`, o agente deve inspecionar somente a imagem indicada; para `type=text`, deve ler somente o TXT indicado. Ele não pode abrir as outras duas fontes, os outros textos nem os CSVs. O primeiro título deve ser exatamente `## Atendimento — CLIENTE_NOME — Lead LEAD_ID`.

Depois que as três análises forem validadas, crie um quarto agente limpo para `04_16_amostragem_qualitativa.md`. Ele recebe somente o prompt de consolidação e as três análises individuais; não recebe as fontes originais nem acrescenta fatos aos casos. Preserve integralmente o título com cliente e lead de cada análise.

Se `prepare` devolver `avaliacao_gestor_path`, forneça esse arquivo somente ao agente de consolidação, nunca aos três agentes individuais. Ele serve para complementar ênfases, hipóteses e recomendações sem ser citado ou copiado.

Finalize os artefatos qualitativos com o script para registrar tipos e hashes das fontes, análises e consolidação.

## Seções quantitativas

Leia `prompts/generativos/manifest.json`. Para cada item de `weekly`, crie um agente limpo com o prompt e os CSVs listados. Expanda `*.csv` somente dentro da pasta da semana. Quando existir uma avaliação do gestor, forneça-a somente aos itens marcados com `manager_context: true`; a ausência desse arquivo não é erro.

Execute `monthly` apenas quando o validador quantitativo indicar que o mês está efetivamente encerrado. Não gere uma nota mensal artificial em semanas comuns.

## Envelope recomendado

```text
Escreva apenas ARQUIVO_SAIDA.
Leia integralmente PROMPT e somente as FONTES listadas.
PASTA_CSV é a pasta semanal informada abaixo.
Não use fatos da conversa, de outras semanas ou conhecimento externo.
Não mencione arquivos internos, coleta manual, agentes, IA, automação, scripts ou APIs no texto entregue.
Substitua a saída existente e não crie arquivos alternativos.
Ao terminar, confirme o caminho gravado e uma validação curta; não cole o texto inteiro na resposta.
```

Se um agente falhar, corrija o problema concreto e repita no máximo uma vez em outro agente limpo. Nunca complete o texto faltante no agente principal.
