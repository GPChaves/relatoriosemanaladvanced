# Blueprint do Relatório de Desempenho Comercial

## 1. Finalidade do documento

Este blueprint define a estrutura, a função e as regras de exibição do relatório periódico de desempenho comercial da Advanced Mecânica. Ele deve ser usado como referência para produzir relatórios consistentes sem transformar o documento em um modelo rígido: os dados, comparações, diagnósticos e recomendações devem mudar conforme o período analisado.

O relatório possui quatro objetivos centrais:

1. medir o volume e a distribuição dos atendimentos;
2. acompanhar o avanço dos leads pelo funil e suas taxas de conversão e perda;
3. identificar mudanças relevantes, possíveis causas e ações recomendadas;
4. avaliar qualitativamente a condução dos atendimentos e a qualidade dos registros no CRM.

## 2. Princípios de elaboração

### 2.1. Separar atividade de entrada de leads

O relatório deve distinguir:

- **leads movimentados:** todos os leads que tiveram alguma atividade no período, independentemente da data de criação;
- **novos leads:** somente os leads criados dentro do período analisado.

Essa separação impede que um consultor com negociações mais longas pareça inativo apenas porque trabalha leads originados em semanas anteriores.

### 2.2. Separar fato, interpretação e recomendação

Cada conclusão deve deixar claro se é:

- **fato:** número diretamente observado nos dados;
- **interpretação:** hipótese ou leitura baseada na combinação dos indicadores;
- **recomendação:** ação proposta para investigar ou melhorar o resultado.

Uma hipótese não deve ser apresentada como causa comprovada sem evidência suficiente.

### 2.3. Considerar o amadurecimento dos leads

Resultados da semana mais recente são provisórios. Leads agendados ou em andamento ainda podem se converter, inclusive em semanas posteriores. Por isso, a taxa imediata de conversão não deve ser tratada automaticamente como definitiva.

### 2.4. Comparar percentuais em pontos percentuais

Quando duas taxas são comparadas, a variação deve ser expressa em **pontos percentuais (p.p.)**.

Exemplo: uma taxa que passa de 32% para 49% aumenta 17 p.p., e não 17%.

Sempre que um percentual semanal possuir uma base comparável na semana anterior, a variação deve ser exibida, mesmo que ela não existisse no relatório original. A comparação não deve ficar entre parênteses junto ao percentual atual: deve ocupar uma coluna própria chamada **Variação (p.p.)**.

O padrão mínimo das tabelas comparativas de taxas é:

| Indicador | Semana anterior | Semana atual | Variação (p.p.) |
|---|---:|---:|---:|
| Exemplo | 32,0% | 49,2% | +17,2 p.p. |

**Fórmula:**

`variação em p.p. = percentual da semana atual − percentual da semana anterior`

**Regras de apresentação:**

- usar sinal `+` para aumento, sinal `−` para redução e `0,0 p.p.` quando não houver mudança;
- manter uma casa decimal, salvo quando a precisão da fonte exigir mais;
- não calcular a variação quando as duas semanas utilizarem universos ou metodologias incompatíveis; nesse caso, mostrar `N/C` e explicar a quebra de comparabilidade;
- para valores absolutos, como número de leads ou minutos de resposta, usar uma coluna de variação na unidade original, nunca em pontos percentuais;
- a obrigação de mostrar a variação nas tabelas não significa que toda mudança precise ser comentada na leitura gerencial. Mudanças pequenas podem permanecer visíveis sem receber destaque analítico.

### 2.5. Exibir somente conteúdo material

Seções analíticas devem priorizar mudanças que tenham relevância operacional, comercial ou gerencial. Não é necessário repetir números estáveis ou produzir recomendações quando os dados não sustentam uma conclusão útil.

## 3. Ordem recomendada do relatório

1. identificação do período;
2. consolidado mensal, quando aplicável;
3. movimentação da semana;
4. novos leads da semana;
5. análise por consultor;
6. tempo médio de resposta;
7. mudanças significativas entre as duas últimas semanas;
8. composição dos leads perdidos;
9. leitura gerencial da semana;
10. análise completa do mês, quando aplicável;
11. auditoria qualitativa dos atendimentos e do CRM;
12. diferenças observadas entre os consultores;
13. limitações da análise e próximos pontos de acompanhamento.

---

## 4. Descrição detalhada de cada item

### 4.1. Identificação do período

**Exibição:** obrigatória.

**Conteúdo:** título do relatório e intervalo exato de datas analisado.

**Objetivo:** delimitar a janela temporal dos dados e impedir que indicadores semanais, mensais e acumulados sejam confundidos.

**Regra:** sempre informar se a semana é completa ou parcial. Quando o relatório fechar um mês, deixar explícito que se trata da última semana e do consolidado mensal.

### 4.2. Mês completo — distribuição por responsável

**Exibição:** condicional. Esta seção aparece somente no relatório referente à última semana do mês.

**Conteúdo:** total de atendimentos ou leads do mês distribuído por responsável, com quantidade e participação percentual. Um usuário genérico da empresa pode aparecer quando existirem leads ainda atribuídos à conta institucional ou sem consultor individual definido.

**Objetivo:** mostrar como o volume mensal foi distribuído entre os responsáveis e revelar concentração, desequilíbrio de carga ou problemas de atribuição no CRM.

**Pergunta respondida:** quem ficou responsável pelos atendimentos do mês e qual foi a participação de cada responsável?

**Cuidados:**

- informar claramente se a contagem representa novos leads, leads movimentados ou outro universo;
- não interpretar participação como produtividade ou qualidade sem considerar volume, maturidade e resultado dos leads;
- investigar percentuais relevantes atribuídos ao usuário genérico da empresa.

### 4.3. Números globais — etapas do lead

**Exibição:** no consolidado do universo analisado; quando representar o mês completo, integra o bloco condicional de fechamento mensal.

**Conteúdo:** quantidade de leads por etapa do funil, separada por responsável e acompanhada do total e do percentual correspondente.

**Objetivo:** apresentar o destino dos leads e medir o desempenho global do funil. A seção permite enxergar quantos converteram, quantos ainda podem avançar e quantos foram perdidos por cada motivo.

**Perguntas respondidas:**

- quantos leads chegaram a serviço iniciado?
- quantos permanecem ativos ou agendados?
- quantos foram perdidos?
- quais motivos concentram as perdas?
- como esses resultados se distribuem entre os consultores?

#### Definição das etapas

- **Serviço iniciado (conversão):** o cliente efetivamente iniciou o serviço. É o principal resultado comercial consumado.
- **Agendado:** o cliente marcou uma data, mas o serviço ainda não começou. Representa uma conversão intermediária e não deve ser somado automaticamente a serviço iniciado.
- **Aguardando resposta / Aguardando resposta 2:** lead ainda aberto, aguardando retorno ou acompanhamento. Não deve ser classificado como perdido enquanto existir uma possibilidade razoável de continuidade.
- **Etapa de leads de entrada:** contato recém-chegado que ainda não recebeu uma classificação mais avançada.
- **Perdido — abandonou a conversa:** o cliente parou de responder antes de uma decisão ou objeção concreta.
- **Perdido — orçamento/preço:** o valor foi o motivo determinante da não contratação.
- **Perdido — serviço:** a demanda não corresponde ao serviço oferecido ou não pôde ser atendida.
- **Perdido — ano incompatível:** o veículo está fora do perfil de ano aceito pela oficina.
- **Perdido — outro:** caso excepcional que não se encaixa nas categorias existentes. Deve ser usado com parcimônia.
- **Perdido — indefinido/sem motivo:** o lead foi encerrado sem registro confiável da causa. Essa classificação sinaliza perda de qualidade de dados.

**Cuidados:** as categorias devem refletir o motivo real da perda. Classificações incorretas distorcem tanto a análise do atendimento quanto a avaliação de campanhas.

### 4.4. Conversão por responsável

**Exibição:** sempre que houver base suficiente para calcular a taxa individual.

**Conteúdo:** taxa de serviços iniciados de cada responsável, calculada sobre o universo de leads atribuído a ele no período correspondente. Quando houver dados comparáveis da semana anterior, apresentar para cada responsável as colunas **Semana anterior**, **Semana atual** e **Variação (p.p.)**.

**Objetivo:** comparar a capacidade de transformar oportunidades em serviços iniciados, sem depender somente do número absoluto de conversões.

**Fórmula:**

`taxa de conversão = serviços iniciados ÷ total de leads do responsável × 100`

**Cuidados:** informar qual universo foi usado no denominador e considerar o estágio de maturação dos leads. Uma taxa baseada em leads recentes pode estar incompleta. A variação só é válida quando as duas taxas foram calculadas com a mesma definição de conversão e o mesmo tipo de universo.

### 4.5. Movimentação na última semana

**Exibição:** obrigatória no relatório semanal.

**Conteúdo:** quantidade de leads efetivamente movimentados por cada consultor durante a semana e sua participação no total. A tabela deve mostrar a participação da semana anterior, a participação da semana atual e a diferença entre elas em uma coluna independente de **Variação (p.p.)**. A variação não deve ser colocada entre parênteses na mesma célula do percentual atual.

**Estrutura mínima da tabela:**

| Responsável | Atendimentos na semana atual | Participação anterior | Participação atual | Variação (p.p.) |
|---|---:|---:|---:|---:|
| Consultor | quantidade | percentual | percentual | atual − anterior |

Quando for útil comparar também o volume absoluto, podem ser acrescentadas as colunas **Atendimentos na semana anterior** e **Variação absoluta**.

**Objetivo:** medir a atividade operacional real dos consultores, incluindo o acompanhamento de leads criados anteriormente.

**Pergunta respondida:** quem trabalhou os atendimentos durante a semana e como o volume foi dividido?

**Cuidados:** esta tabela não representa necessariamente entrada de novos leads. Ela mede atividade no período. Todas as participações percentuais devem usar o total de leads movimentados da respectiva semana como denominador.

### 4.6. Nota metodológica sobre movimentação

**Exibição:** obrigatória sempre que houver risco de confundir leads movimentados com leads novos; especialmente importante quando houver mudança de metodologia.

**Conteúdo:** explicação curta sobre o universo considerado e eventuais alterações na forma de apuração.

**Objetivo:** garantir comparabilidade e transparência. O leitor precisa saber por que os números podem diferir de relatórios anteriores.

**Regra:** uma mudança de método deve ser destacada e seus efeitos sobre a comparação histórica precisam ser reconhecidos.

### 4.7. Novos leads na semana

**Exibição:** obrigatória no relatório semanal.

**Conteúdo:** número de leads criados na semana, distribuído por responsável, com participação percentual e comparação com a semana anterior. Para cada responsável, apresentar **Participação anterior**, **Participação atual** e **Variação (p.p.)**. Para o total de novos leads, que é um volume e não uma taxa, apresentar a mudança em quantidade absoluta e, se desejado, a variação percentual relativa em coluna separada claramente identificada.

**Estrutura recomendada da tabela:**

| Responsável | Novos leads atuais | Participação anterior | Participação atual | Variação (p.p.) |
|---|---:|---:|---:|---:|

**Objetivo:** medir o fluxo de novas oportunidades comerciais e verificar se a aquisição de leads está crescendo, estável ou caindo.

**Perguntas respondidas:**

- quantos novos contatos entraram?
- como foram distribuídos?
- o volume mudou de forma relevante?

**Cuidados:** divergências entre plataformas de anúncios e CRM devem ser tratadas como indício de possível gargalo, não como prova automática de falha. Devem ser verificadas etapas como anúncio, site, clique no WhatsApp, início da conversa, integração e registro no CRM. Não expressar a mudança da quantidade total de leads em pontos percentuais; pontos percentuais são usados apenas para a diferença entre taxas ou participações.

### 4.8. Análise por consultor

**Exibição:** obrigatória quando houver volume suficiente por consultor.

**Conteúdo:** para cada consultor, tabela com quantidade e percentual de leads em cada etapa, seguida de uma leitura individual. Sempre que houver dados comparáveis da semana anterior, cada taxa por etapa deve ser acompanhada pelas colunas **% na semana anterior**, **% na semana atual** e **Variação (p.p.)**.

**Estrutura recomendada da tabela individual:**

| Etapa do lead | Quantidade atual | % anterior | % atual | Variação (p.p.) |
|---|---:|---:|---:|---:|

**Objetivo:** identificar diferenças de desempenho e de condução que ficam escondidas no consolidado da equipe.

**A tabela individual deve permitir avaliar:**

- conversão em serviço iniciado;
- agendamentos;
- leads em acompanhamento;
- abandono de conversas;
- composição das perdas;
- possíveis diferenças no tempo de vida do lead.

#### Leitura individual do consultor

**Objetivo:** interpretar os indicadores do consultor sem produzir um ranking automático. A leitura deve destacar pontos fortes, pontos de atenção e hipóteses que mereçam acompanhamento.

**Cuidados:**

- considerar a quantidade de atendimentos e o estágio dos leads;
- não penalizar automaticamente ciclos de venda mais longos;
- diferenciar alterações administrativas no CRM de participação efetiva na negociação;
- usar, em cada semana, o total de atendimentos daquele consultor como denominador das taxas por etapa;
- evitar conclusões de comportamento recorrente com amostra pequena.

### 4.9. Tempo médio de resposta

**Exibição:** quando o dado estiver disponível e for comparável.

**Conteúdo:** somente o responsável, o tempo da semana atual e a mudança em minutos. O valor da semana anterior é usado para calcular a mudança, mas não aparece no PDF.

**Objetivo:** acompanhar a agilidade do atendimento e investigar sua possível relação com abandono, engajamento e conversão.

**Cuidados:** definir exatamente o que inicia e encerra a contagem. A comparação perde validade se a metodologia variar entre consultores ou semanas. Como tempo não é percentual, sua variação deve ser mostrada em minutos ou na unidade adotada, e não em pontos percentuais.

### 4.10. Mudanças significativas entre as duas últimas semanas

**Exibição:** dinâmica. A seção deve conter somente mudanças materialmente relevantes entre as duas semanas mais recentes.

**Conteúdo:** tabela ou lista com o indicador, valor anterior, valor atual e uma coluna dedicada de variação. Para taxas, a coluna deve se chamar **Variação (p.p.)**; para volumes, valores financeiros ou tempo, deve indicar a unidade correspondente. Os indicadores não são fixos: entram aqueles que realmente se destacarem no período.

**Objetivo:** funcionar como um filtro gerencial, direcionando a atenção para alterações que possam exigir explicação, decisão ou acompanhamento.

**Critérios para inclusão:**

- grande variação absoluta ou em pontos percentuais;
- mudança de tendência ou reversão de comportamento;
- impacto relevante em conversão, receita potencial, qualidade do lead ou operação;
- anomalia em relação ao histórico disponível;
- mudança que gere uma hipótese ou ação gerencial útil.

**Exemplos possíveis:** volume de leads, participação por consultor, conversão, agendamentos, abandono, perdas, tempo de resposta ou qualquer outro indicador pertinente.

**Regra essencial:** um indicador que quase não mudou não deve ser incluído apenas porque apareceu em relatórios anteriores. Em contrapartida, uma forte mudança em agendamentos ou em qualquer outra métrica deve entrar mesmo que ela não faça parte de uma lista predefinida.

**Cuidados:** informar se a variação é absoluta, percentual ou em pontos percentuais e considerar diferenças de tamanho da amostra. Nunca misturar o percentual atual e a variação na mesma célula.

### 4.11. Composição dos leads perdidos

**Exibição:** quando houver quantidade suficiente de perdas para produzir percentuais interpretáveis.

**Conteúdo:** comparação dos motivos de perda nas duas semanas mais recentes, com quantidade, participação dentro do total de perdidos e uma coluna dedicada de **Variação (p.p.)** para cada motivo.

**Estrutura mínima da tabela:**

| Motivo da perda | Quantidade anterior | % anterior | Quantidade atual | % atual | Variação (p.p.) |
|---|---:|---:|---:|---:|---:|

**Objetivo:** identificar se a natureza das perdas está mudando. Isso ajuda a separar problemas de atendimento, preço, segmentação, serviço oferecido, perfil do veículo e qualidade do registro no CRM.

**Pergunta respondida:** por quais razões os leads estão sendo perdidos e quais motivos ganharam ou perderam importância?

**Cuidados:** a porcentagem deve usar como base o total de leads perdidos de cada semana, e não o total geral de leads. A variação em pontos percentuais é calculada como `% atual − % anterior`. Motivos genéricos ou sem motivo devem ser auditados.

### 4.12. Leitura gerencial da semana

**Exibição:** obrigatória, desde que existam conclusões sustentadas pelos dados.

**Conteúdo:** síntese contextual dos fatos mais importantes, suas possíveis explicações, riscos, oportunidades e ações recomendadas. Os pontos abordados mudam a cada período.

**Objetivo:** transformar os dados do relatório em orientação para decisão. Esta seção deve explicar o que merece atenção, por que importa e qual deve ser o próximo passo.

**Estrutura recomendada para cada insight:**

1. apresentar o dado relevante;
2. explicar o possível significado;
3. registrar fatores que limitam a conclusão;
4. recomendar uma verificação, correção ou acompanhamento.

**Regra essencial:** não existe uma lista fixa de conclusões. Queda de leads, aumento de agendamentos, mudança em conversão, melhora no abandono ou qualquer outro ponto só deve aparecer se for relevante no período analisado e justificar uma leitura ou recomendação.

**Cuidados:**

- não repetir todas as tabelas em formato de texto;
- priorizar poucos insights acionáveis;
- diferenciar correlação de causa;
- indicar quando a investigação depende de campanhas, site, WhatsApp, CRM ou processo comercial.

### 4.13. Análise completa do mês

**Exibição:** condicional. Esta seção aparece somente no relatório da última semana do mês.

**Conteúdo:** comparação de todas as semanas do mês, seguida do consolidado mensal. Deve incluir, conforme disponibilidade, novos leads, serviços iniciados, agendados, perdidos e em andamento. Para cada taxa semanal, mostrar também a variação em pontos percentuais em relação à semana imediatamente anterior, seja em coluna adjacente ou em uma tabela comparativa complementar.

**Objetivo:** fornecer uma visão do comportamento do mês inteiro, identificar semanas fortes ou fracas e contextualizar o resultado mensal para além da última semana.

**Definição de “em andamento”:** agrupamento de etapas ainda abertas, como Aguardando resposta, Aguardando resposta 2 e etapa de entrada.

**A leitura mensal deve identificar:**

- maior e menor volume semanal;
- melhor e pior desempenho entre semanas já amadurecidas;
- alterações relevantes nas taxas do funil;
- quantidade de leads ainda não concluídos;
- resultado consolidado do mês;
- limitações de comparação, como semanas parciais e falta de histórico de outros meses.

**Cuidados:**

- não comparar diretamente uma semana parcial com semanas completas sem ressalva;
- não tratar a conversão da última semana como definitiva;
- mostrar `N/A` para a primeira semana do mês quando não houver uma semana anterior dentro da análise; se o relatório utilizar a última semana do mês anterior como base, isso deve ser informado explicitamente;
- não calcular variação em pontos percentuais para volumes absolutos, como quantidade de novos leads;
- reconhecer sazonalidade e ausência de referência histórica quando aplicável;
- manter consistência entre os totais semanais e o total do mês.

### 4.14. Resumo consolidado do mês

**Exibição:** dentro da análise completa do mês, portanto somente na última semana.

**Conteúdo:** principais totais e taxas do mês, como novos leads, serviços iniciados, perdidos, agendados e em andamento.

**Objetivo:** permitir que o leitor compreenda o resultado mensal em poucos números, sem precisar reconstruí-lo a partir das tabelas semanais.

### 4.15. Auditoria de uso do CRM

**Exibição:** quando a análise identificar problemas de classificação, movimentação, atribuição ou encerramento de leads.

**Conteúdo:** exemplos documentados, preferencialmente com captura de tela, descrição do registro encontrado e orientação sobre a classificação correta.

**Objetivo:** melhorar a qualidade dos dados e assegurar que o funil represente o estado real das oportunidades. Um CRM mal preenchido pode criar falsas perdas, atribuir conversões incorretamente e prejudicar todas as análises seguintes.

**Pontos a verificar:**

- lead encerrado enquanto ainda existe possibilidade razoável de retorno;
- follow-up ou revenda colocados no funil inadequado;
- reagendamento classificado como perda;
- motivo de perda incompatível com a conversa;
- responsável no CRM diferente de quem conduziu o atendimento.

### 4.16. Amostragem qualitativa dos atendimentos

**Exibição:** obrigatória quando existir a pasta manual da semana com as três conversas de atendimento; indisponível quando não houver amostra documentada.

**Conteúdo:** análise de exatamente três conversas completas escolhidas para a semana. Cada conversa deve ser anonimizada localmente e enviada isoladamente a um agente diferente, sem acesso aos outros casos. A saída deve registrar o contexto, pontos positivos, oportunidades de melhoria, melhor próximo passo, exemplo curto de resposta e limites do material.

**Entrada manual:** `entradas_manuais/atendimentos/AAAA-MM-DD/`, com exatamente três arquivos TXT em UTF-8. Qualquer outra quantidade bloqueia a geração. As conversas são ligadas às análises por SHA-256; trocar um texto invalida a análise antiga.

**Saídas:** três análises individuais em `generativos/atendimentos/` e um arquivo consolidado `04_16_amostragem_qualitativa.md`. As conversas originais não são inseridas no PDF.

**Objetivo:** avaliar aspectos que as métricas não conseguem medir, como qualidade da comunicação, domínio técnico, entendimento da objeção, defesa de valor, proatividade, acompanhamento e pressão comercial.

**Critérios possíveis de avaliação:**

- tempo e clareza da resposta;
- investigação da necessidade real;
- explicação do serviço e das peças;
- defesa do orçamento antes do desconto;
- tratamento da objeção;
- oferta de solução concreta;
- acompanhamento e retomada;
- momento correto de encerrar o lead;
- precisão do registro no CRM.

**Cuidados:** antes de qualquer chamada à IA, o script deve remover localmente telefones, e-mails, documentos, placas, CEP, dados bancários, endereços em campos e nomes presentes nos cabeçalhos dos participantes. As análises não devem reconstruir nem reproduzir os dados removidos. Três casos geram indícios e ações de treinamento, não conclusões universais sobre a equipe.

### 4.17. Diferenças observadas entre os consultores

**Exibição:** quando houver evidência quantitativa e/ou qualitativa suficiente para descrever tendências.

**Conteúdo:** síntese comparativa de estilos, pontos fortes, riscos e comportamentos observados em cada consultor.

**Objetivo:** orientar acompanhamento, treinamento, divisão de responsabilidades e eventual individualização dos atendimentos.

**Regra:** apresentar tendências, não rótulos definitivos. Não produzir ranking qualitativo quando a amostra não for representativa.

**Cuidados:** separar claramente:

- quem realizou o contato comercial;
- quem movimentou ou organizou o lead no CRM;
- quem contribuiu para a conversão;
- quais comportamentos foram observados apenas em casos isolados.

### 4.18. Limitações e próximos passos

**Exibição:** obrigatória sempre que houver fatores que reduzam a segurança da análise.

**Conteúdo:** ressalvas sobre tamanho da amostra, maturidade dos leads, mudança de metodologia, semanas parciais, qualidade do CRM, sazonalidade e ausência de histórico. Também deve registrar o que será investigado ou acompanhado no próximo ciclo.

**Objetivo:** impedir conclusões excessivas e transformar incertezas em um plano de validação.

---

## 5. Regras de seleção: seções fixas, dinâmicas e condicionais

| Tipo | Seções | Regra |
|---|---|---|
| Fixa | Identificação do período, movimentação semanal, novos leads, análise por consultor | Devem formar o núcleo do relatório semanal, desde que os dados existam. |
| Dinâmica | Mudanças significativas, composição das perdas, leitura gerencial, auditoria qualitativa, diferenças entre consultores | Conteúdo escolhido conforme relevância, materialidade e evidência do período. |
| Condicional mensal | Mês completo, números globais mensais, análise completa do mês e resumo mensal | Exibir somente no relatório referente à última semana do mês. |

## 6. Critérios mínimos de qualidade

Antes de concluir o relatório, verificar:

- se o período e o universo de cada tabela estão explícitos;
- se leads movimentados e novos leads não foram confundidos;
- se quantidades, totais e percentuais fecham corretamente;
- se variações de taxas estão expressas em pontos percentuais;
- se toda taxa semanal comparável contém semana anterior, semana atual e uma coluna própria de **Variação (p.p.)**;
- se nenhuma variação foi apresentada entre parênteses na célula do percentual atual;
- se variações de volume e tempo estão nas unidades corretas, e não em pontos percentuais;
- se a última semana foi tratada como dado ainda em maturação;
- se apenas mudanças realmente relevantes entraram na seção comparativa;
- se a leitura gerencial é contextual e acionável;
- se hipóteses estão identificadas como hipóteses;
- se motivos de perda representam corretamente as conversas;
- se conclusões qualitativas respeitam o tamanho da amostra;
- se as seções mensais aparecem apenas no fechamento do mês;
- se dados pessoais e capturas de tela têm circulação adequada.

## 7. Resultado esperado

Ao final, o relatório deve permitir que a gestão responda rapidamente:

1. quantos leads entraram e quantos foram trabalhados;
2. como os atendimentos foram distribuídos;
3. quantos converteram, ficaram em andamento ou foram perdidos;
4. por que os leads foram perdidos;
5. quais mudanças do período são realmente importantes;
6. que hipóteses explicam essas mudanças;
7. quais ações devem ser tomadas;
8. como melhorar a condução comercial e a qualidade dos registros no CRM.
