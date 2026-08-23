# Índice dos prompts generativos

Este diretório contém um prompt autossuficiente para cada seção generativa do relatório de desempenho comercial.

## Contrato de execução

Os caminhos da semana não ficam gravados nos prompts. O executor fornece a cada agente, no envelope da tarefa, a pasta dos CSVs, o arquivo de saída e uma referência editorial opcional. O arquivo `manifest.json` relaciona cada prompt às entradas e à saída estável.

Cada texto deve ser produzido por um agente com contexto limpo. O agente lê somente o prompt e as fontes declaradas para sua tarefa. Todos os números e conclusões devem vir dos CSVs fornecidos.

## Prompts e arquivos de saída

| Seção | Prompt | Saída estável | Aplicabilidade |
|---|---|---|---|
| 4.8 | `04_08_leitura_consultores.prompt.md` | `04_08_leitura_consultores.md` | Quando houver volume por consultor |
| 4.10 | `04_10_mudancas_significativas.prompt.md` | `04_10_mudancas_significativas.md` | Quando houver mudanças materiais |
| 4.12 | `04_12_leitura_gerencial_semana.prompt.md` | `04_12_leitura_gerencial_semana.md` | Sempre que houver conclusões sustentadas |
| 4.13 | `04_13_leitura_gerencial_mes.prompt.md` | `04_13_leitura_gerencial_mes.md` | Apenas em fechamento mensal |
| 4.15 | `04_15_auditoria_crm.prompt.md` | `04_15_auditoria_crm.md` | Quando os dados sustentarem alertas de uso do CRM |
| 4.16 | `04_16_amostragem_qualitativa.prompt.md` | `04_16_amostragem_qualitativa.md` | Quando houver dados de conversas ou amostra documentada |
| 4.16 individual | `04_16_analise_atendimento_individual.prompt.md` | `atendimentos/01_analise.md` a `03_analise.md` | Exatamente três prints, cada um analisado isoladamente |
| 4.17 | `04_17_diferencas_consultores.prompt.md` | `04_17_diferencas_consultores.md` | Quando houver evidência comparável suficiente |
| 4.18 | `04_18_limitacoes_proximos_passos.prompt.md` | `04_18_limitacoes_proximos_passos.md` | Sempre que houver limitações materiais |

## Como regenerar

1. Leia `manifest.json` e selecione as tarefas semanais, qualitativas e, quando aplicável, mensais.
2. Crie um agente limpo por texto e forneça os caminhos absolutos de suas entradas e saída.
3. Mantenha o nome estável do arquivo de saída. Não acrescente datas, versões, `(1)` ou timestamps.
4. Substitua integralmente uma saída anterior da mesma semana.
5. Para a seção 4.16, analise cada print em um agente isolado antes de criar a consolidação em um quarto agente limpo.

## Regras comuns

- Usar somente fatos presentes nos CSVs configurados.
- Usar o PDF apenas como referência editorial, nunca como fonte de valores.
- Não atribuir causalidade sem evidência; formular hipóteses como hipóteses.
- Distinguir volumes absolutos, percentuais e pontos percentuais.
- Considerar maturação dos leads, semanas parciais, tamanho da amostra e metodologia.
- Não expor token, telefone, nome de cliente, conteúdo de mensagem ou outro dado pessoal.
- Produzir Markdown pronto para inserção no relatório.
- Sobrescrever o arquivo exato configurado e não criar arquivos alternativos.
- Escrever para donos de oficina mecânica, com frases curtas e termos do dia a dia.
- Preferir “leads que entraram” a “coorte”, “conferir” a “reconciliar” e explicar qualquer termo técnico indispensável.
- Cortar repetições sem retirar números, limites dos dados, hipóteses ou ações práticas.
