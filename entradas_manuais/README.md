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

## Configuração da IA

Adicione ao `env.txt`:

```text
OPENAI_API_KEY=sua_chave_da_api
OPENAI_MODEL=gpt-5.6-terra
```

Sem `OPENAI_MODEL`, o script usa `gpt-5.6-terra`. A chave da OpenAI é diferente do token da Kommo.

## Execução

Depois de preencher as duas pastas da semana:

```powershell
python relatorio.py --week-start AAAA-MM-DD
python gerar_relatorio_final.py --week-start AAAA-MM-DD
```

O segundo comando valida os três prints, abre três análises independentes em paralelo, cria a consolidação e só então gera o PDF. Se uma saída já existir mas estiver desatualizada, o script pergunta antes de sobrescrevê-la. Para validar sem gerar nem sobrescrever, use `--validate-only` no segundo comando.
