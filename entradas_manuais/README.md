# Entradas manuais do relatório

As entradas ficam separadas por semana, usando como pasta o primeiro dia da semana no formato `AAAA-MM-DD`.

## Tempo de resposta

Copie o modelo para:

`entradas_manuais/tempo_resposta/AAAA-MM-DD/tempo_resposta.csv`

O CSV aceita `;` ou `,` como separador. Use `N/C` quando uma das semanas não tiver medição. O arquivo manual tem prioridade sobre a tentativa de leitura das conversas pela Kommo e nunca é alterado pelo script.

Substitua os valores do modelo antes de rodar: cada responsável precisa ter pelo menos um tempo médio medido. Quantidades e tempos não podem ser negativos, e o mesmo responsável não pode aparecer duas vezes.

## Prints de atendimento

Coloque exatamente três arquivos PNG ou JPG em:

`entradas_manuais/atendimentos/AAAA-MM-DD/`

Exemplo:

- `01.png`
- `02.png`
- `03.png`

Cada print é enviado separadamente para um agente de análise com visão. Os três agentes trabalham em paralelo e não veem os outros casos. As saídas ficam em:

`outputs/AAAA/AAAA-MM-DD/generativos/atendimentos/`

O arquivo consolidado usado pelo PDF é `04_16_amostragem_qualitativa.md`.

Os prints originais não entram no PDF. Antes de colocá-los na pasta, recorte ou cubra nome, telefone, placa, endereço e qualquer outro dado pessoal que não seja necessário para a análise.

## Análise por IA

Os scripts não chamam a API da OpenAI. A skill `gerar-relatorio-comercial` cria um subagente Codex isolado para cada print e outro para a consolidação. Assim, cada caso recebe somente sua própria imagem e o prompt correspondente.

## Execução

O fluxo recomendado é invocar a skill `gerar-relatorio-comercial`. Para validar manualmente os artefatos qualitativos:

```powershell
python processar_atendimentos.py prepare --week-start AAAA-MM-DD
# Os subagentes gravam as três análises e a consolidação.
python processar_atendimentos.py finalize --week-start AAAA-MM-DD
python processar_atendimentos.py validate --week-start AAAA-MM-DD
```

O comando `finalize` registra hashes das imagens, dos textos individuais, do consolidado e do prompt. Qualquer alteração posterior faz `validate` falhar e exige nova análise.
