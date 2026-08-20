# Índice dos prompts generativos

Este diretório contém um prompt autossuficiente para cada seção generativa do relatório de desempenho comercial.

## Referência configurada

- Pasta dos CSVs: `C:\Users\admin\Desktop\Advanced\Relatorio foda\outputs\2026\2026-07-27`
- Pasta dos textos gerados: `C:\Users\admin\Desktop\Advanced\Relatorio foda\outputs\2026\2026-07-27\generativos`
- PDF de referência editorial: `C:\Users\admin\Downloads\Rel. Desempenho Jul 27-31.pdf`

O PDF serve apenas para orientar o tom, a profundidade e o formato. Todos os números e conclusões devem vir dos CSVs da pasta configurada.

## Prompts e arquivos de saída

| Seção | Prompt | Saída estável | Aplicabilidade |
|---|---|---|---|
| 4.8 | `04_08_leitura_consultores.prompt.md` | `04_08_leitura_consultores.md` | Quando houver volume por consultor |
| 4.10 | `04_10_mudancas_significativas.prompt.md` | `04_10_mudancas_significativas.md` | Quando houver mudanças materiais |
| 4.12 | `04_12_leitura_gerencial_semana.prompt.md` | `04_12_leitura_gerencial_semana.md` | Sempre que houver conclusões sustentadas |
| 4.13 | `04_13_leitura_gerencial_mes.prompt.md` | `04_13_leitura_gerencial_mes.md` | Apenas em fechamento mensal |
| 4.15 | `04_15_auditoria_crm.prompt.md` | `04_15_auditoria_crm.md` | Quando os dados sustentarem alertas de uso do CRM |
| 4.16 | `04_16_amostragem_qualitativa.prompt.md` | `04_16_amostragem_qualitativa.md` | Quando houver dados de conversas ou amostra documentada |
| 4.16 individual | `04_16_analise_atendimento_individual.prompt.md` | `atendimentos/01_analise.md` a `03_analise.md` | Exatamente três conversas anonimizadas, cada uma analisada isoladamente |
| 4.17 | `04_17_diferencas_consultores.prompt.md` | `04_17_diferencas_consultores.md` | Quando houver evidência comparável suficiente |
| 4.18 | `04_18_limitacoes_proximos_passos.prompt.md` | `04_18_limitacoes_proximos_passos.md` | Sempre que houver limitações materiais |

## Como regenerar

1. Copie a pasta de prompts ou altere, dentro de cada prompt, os campos `PASTA_CSV` e `ARQUIVO_SAIDA` para a semana desejada.
2. Mantenha o nome estável do arquivo de saída. Não acrescente datas, versões, `(1)` ou timestamps ao nome.
3. Execute cada prompt separadamente. O agente deve ler os CSVs diretamente da pasta indicada.
4. Se o arquivo de saída já existir, ele deve ser substituído integralmente. Essa sobrescrita é deliberada e evita duplicatas.
5. Revise primeiro as seções 4.8, 4.10 e 4.13. As seções 4.12, 4.17 e 4.18 podem usar as mesmas fontes, mas devem continuar compreensíveis de forma independente.
6. A seção 4.16 não pode ser produzida a partir de métricas agregadas. Sem amostra de conversas, o resultado correto é uma nota de indisponibilidade, nunca uma análise inventada.

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
