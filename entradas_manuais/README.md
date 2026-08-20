# Entradas manuais do relatório

As entradas ficam separadas por semana, usando como pasta o primeiro dia da semana no formato `AAAA-MM-DD`.

## Tempo de resposta

Copie o modelo para:

`entradas_manuais/tempo_resposta/AAAA-MM-DD/tempo_resposta.csv`

O CSV aceita `;` ou `,` como separador. Use `N/C` quando uma das semanas não tiver medição. O arquivo manual tem prioridade sobre a tentativa de leitura das conversas pela Kommo e nunca é alterado pelo script.

Substitua os valores do modelo antes de rodar: cada responsável precisa ter pelo menos um tempo médio medido. Os tempos não podem ser negativos, e o mesmo responsável não pode aparecer duas vezes. As quantidades de conversas são opcionais e não aparecem no PDF.

## Conversas de atendimento

Coloque exatamente três arquivos de texto UTF-8 em:

`entradas_manuais/atendimentos/AAAA-MM-DD/`

Exemplo:

- `01.txt`
- `02.txt`
- `03.txt`

Cole uma conversa completa em cada arquivo. Pode ser uma exportação do WhatsApp ou um texto no formato `Cliente: mensagem` / `Oficina: mensagem`.

Antes de qualquer envio à OpenAI, o script remove localmente telefones, e-mails, CPF, CNPJ, cartões, placas, CEP, endereços informados em campos, chaves Pix e nomes presentes nos cabeçalhos dos participantes. Os participantes passam a ser identificados como `CLIENTE`, `OFICINA` ou `PARTICIPANTE 1`, por exemplo.

Cada conversa já anonimizada é enviada separadamente para um agente. Os três agentes trabalham em paralelo e não veem os outros casos. As saídas ficam em:

`outputs/AAAA/AAAA-MM-DD/generativos/atendimentos/`

O arquivo consolidado usado pelo PDF é `04_16_amostragem_qualitativa.md`.

As conversas originais não entram no PDF. A anonimização automática cobre os formatos mais comuns, mas textos livres podem conter dados incomuns. Por isso, não inclua documentos, senhas, dados de cartão ou qualquer informação que não seja necessária para avaliar o atendimento.

## Configuração da IA

Adicione ao `env.txt`:

```text
OPENAI_API_KEY=sua_chave_da_api
OPENAI_MODEL=gpt-5.6-terra
```

Sem `OPENAI_MODEL`, o script usa `gpt-5.6-terra`. A chave da OpenAI é diferente do token da Kommo.

## Campanha do Google

Quando houver dados de campanha, salve o CSV semanal em:

`entradas_manuais/campanha_google/AAAA-MM-DD/campanha_google.csv`

Se esse arquivo existir, o gerador adiciona automaticamente ao final do relatório uma página com os indicadores da campanha e o aviso do período.

## Execução

Depois de preencher as duas pastas da semana:

```powershell
python relatorio.py --week-start AAAA-MM-DD
python gerar_relatorio_final.py --week-start AAAA-MM-DD
```

O segundo comando valida as três conversas, anonimiza os textos, abre três análises independentes em paralelo, cria a consolidação e só então gera o PDF. Se uma saída já existir mas estiver desatualizada, o script pergunta antes de sobrescrevê-la. Para validar sem gerar nem sobrescrever, use `--validate-only` no segundo comando.
