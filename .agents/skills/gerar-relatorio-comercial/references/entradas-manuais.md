# Entradas manuais

Use esta referência quando a semana ainda não tiver todas as entradas manuais.

## Tempo de primeira resposta

Peça uma linha por consultor com estes cinco campos:

1. responsável;
2. conversas medidas na semana anterior;
3. tempo médio, em minutos, na semana anterior;
4. conversas medidas na semana atual;
5. tempo médio, em minutos, na semana atual.

Oriente o usuário a obter os números no relatório do canal de atendimento usado pela oficina, medindo o intervalo entre a primeira mensagem recebida do cliente e a primeira resposta humana. As duas semanas precisam usar a mesma definição. Aceite `N/C` para um período sem medição, mas cada responsável precisa ter pelo menos um tempo informado.

Grave em `entradas_manuais/tempo_resposta/AAAA-MM-DD/tempo_resposta.csv`, separado por ponto e vírgula, com o cabeçalho:

```text
responsavel_nome;conversas_anterior;tempo_medio_minutos_anterior;conversas_atual;tempo_medio_minutos_atual
```

Não invente quantidades ausentes e não converta `N/C` para zero. Rejeite valores negativos, responsáveis duplicados e linhas sem nenhum tempo medido. Aceite vírgula ou ponto como separador decimal, conforme o validador do projeto.

## Três prints de atendimento

Peça exatamente três PNG ou JPG, cada um representando um atendimento diferente. Explique que o usuário deve:

- mostrar contexto suficiente para avaliar abordagem, objeção e próximo passo;
- recortar ou cobrir nome, telefone, placa, endereço e outros dados pessoais;
- não juntar os três casos em uma única imagem.

Salve em `entradas_manuais/atendimentos/AAAA-MM-DD/` como `01`, `02` e `03`, preservando uma extensão suportada. Considere uma imagem estruturalmente válida somente quando o comando `processar_atendimentos.py prepare` aceitar sua assinatura e a contagem. Se os anexos não estiverem acessíveis como arquivos locais, peça que sejam anexados novamente; não crie imagens substitutas.

## Regra de retomada

Pergunte em uma única mensagem por tudo que estiver ausente. Depois da resposta, salve e valide novamente. Não inicie Kommo, XLSX ou geração de texto enquanto uma entrada obrigatória estiver ausente ou inválida.
