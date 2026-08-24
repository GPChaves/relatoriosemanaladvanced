# Entradas manuais do relatório

As entradas ficam separadas por semana, usando como pasta o primeiro dia da semana no formato `AAAA-MM-DD`.

## Tempo de resposta

Copie o modelo para:

`entradas_manuais/tempo_resposta/AAAA-MM-DD/tempo_resposta.csv`

O CSV aceita `;` ou `,` como separador. Use `N/C` quando uma das semanas não tiver medição. Informe somente o tempo médio de cada semana; o indicador deve considerar todas as conversas ocorridas no respectivo período.

Substitua os valores do modelo antes de rodar: cada responsável precisa ter pelo menos um tempo médio medido. Tempos não podem ser negativos, e o mesmo responsável não pode aparecer duas vezes. Não informe quantidade de conversas.

## Amostras de atendimento

Coloque exatamente três atendimentos em qualquer combinação de PNG, JPG ou TXT em:

`entradas_manuais/atendimentos/AAAA-MM-DD/`

Exemplo:

- `01.png`
- `02.txt`
- `03.jpg`

Cada fonte é enviada separadamente para um agente de análise. Os três agentes trabalham em paralelo e não veem os outros casos. Para uma conversa copiada e colada, grave somente o atendimento correspondente em TXT UTF-8, mantendo a ordem das mensagens e, quando possível, identificando `Cliente:` e `Consultor:`. As saídas ficam em:

`outputs/AAAA/AAAA-MM-DD/generativos/atendimentos/`

O arquivo consolidado usado pelo PDF é `04_16_amostragem_qualitativa.md`.

As fontes originais não entram no PDF. Antes de salvá-las, recorte, cubra ou remova nome, telefone, placa, endereço e qualquer outro dado pessoal que não seja necessário para a análise.

## Análise por IA

Os scripts não chamam a API da OpenAI. A skill `gerar-relatorio-comercial` cria um subagente Codex isolado para cada fonte e outro para a consolidação. Assim, cada caso recebe somente sua própria imagem ou transcrição e o prompt correspondente.

## Execução

O fluxo recomendado é invocar a skill `gerar-relatorio-comercial`. Para validar manualmente os artefatos qualitativos:

```powershell
python processar_atendimentos.py prepare --week-start AAAA-MM-DD
# Os subagentes gravam as três análises e a consolidação.
python processar_atendimentos.py finalize --week-start AAAA-MM-DD
python processar_atendimentos.py validate --week-start AAAA-MM-DD
```

O comando `finalize` registra hashes das fontes, das análises individuais, do consolidado e do prompt. Qualquer alteração posterior faz `validate` falhar e exige nova análise.
