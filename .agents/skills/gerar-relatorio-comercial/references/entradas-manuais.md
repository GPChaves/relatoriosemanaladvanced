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

## Três fontes de atendimento

Peça exatamente três casos, cada um representando um atendimento diferente. Cada caso pode chegar como:

- PNG ou JPG da conversa;
- conversa copiada e colada diretamente na resposta do usuário.

Para imagens, explique que o usuário deve:

- mostrar contexto suficiente para avaliar abordagem, objeção e próximo passo;
- recortar ou cobrir nome, telefone, placa, endereço e outros dados pessoais;
- não juntar os três casos em uma única imagem.

Para texto colado, peça que os três casos sejam separados e identificados como `Atendimento 1`, `Atendimento 2` e `Atendimento 3`. Preserve a ordem das mensagens, identifique `Cliente:` e `Consultor:` quando isso estiver claro e remova os mesmos dados pessoais antes de salvar. Não complete trechos ausentes nem corrija o conteúdo da conversa.

Salve em `entradas_manuais/atendimentos/AAAA-MM-DD/` como `01`, `02` e `03`: preserve PNG/JPG para anexos e use TXT UTF-8 para texto colado. Aceite qualquer combinação dos formatos, desde que existam exatamente três fontes. Considere a entrada válida somente quando `processar_atendimentos.py prepare` aceitar tipos, conteúdo e contagem. Se um anexo não estiver acessível como arquivo local, peça que seja anexado novamente; não crie substitutos.

## Regra de retomada

Pergunte em uma única mensagem por tudo que estiver ausente. Depois da resposta, salve e valide novamente. Não inicie Kommo, XLSX ou geração de texto enquanto uma entrada obrigatória estiver ausente ou inválida.
