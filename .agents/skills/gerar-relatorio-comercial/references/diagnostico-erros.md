# Diagnóstico de erros

Use esta referência somente depois de um comando falhar. Mostre ao usuário o comando que falhou, a parte útil de `stderr` e uma correção concreta. Nunca exponha tokens nem o conteúdo integral das amostras.

## Entradas

- Data não é segunda-feira: peça o primeiro dia da semana no formato `AAAA-MM-DD`.
- CSV ausente ou inválido: mostre o caminho esperado e os campos problemáticos; volte à coleta manual.
- Quantidade de fontes diferente de três: informe os arquivos encontrados e peça a correção da pasta.
- Fonte inválida: peça PNG/JPG legível ou TXT UTF-8 não vazio, sempre anonimizado.
- Hash desatualizado: uma fonte ou análise mudou; gere novamente apenas os artefatos qualitativos da semana.

## Kommo

- `KOMMO_TOKEN` ou `KOMMO_BASE_URL` ausente: peça ao usuário para configurar `env.txt`; nunca solicite que cole o token na conversa.
- HTTP 401/403: o token expirou ou não possui acesso; oriente renovar a credencial e conferir permissões de leitura.
- HTTP 429 ou erro 5xx: espere apenas o tempo indicado pelo servidor e tente mais uma vez. Se repetir, pare e reporte indisponibilidade.
- Escopo de histórico de chat ausente: use o CSV manual de tempo de resposta; não estime a métrica.
- Funil não encontrado: peça o nome correto ou ajuste a configuração, sem escolher outro funil silenciosamente.
- Campo personalizado `Usuário responsável` ausente ou duplicado: peça a correção do cadastro de campos da Kommo; não use o responsável padrão nem o autor do evento como substituto.
- Mais de um valor em `Usuário responsável`: identifique o lead informado no erro e peça a correção da ficha antes de executar novamente.

## Exportação XLSX

- Colunas ausentes: liste as colunas exigidas e peça uma nova exportação completa do Kommo.
- Data de fechamento ausente: peça que o usuário inclua uma única coluna aceita pelo importador (`Data Fechada`, `Data de fechamento`, `Data fechada` ou `Fechado em`).
- Lead em `Serviço iniciado` ou `Perdido` sem data de fechamento: identifique as linhas e peça a correção ou nova exportação; não use `Última modificação` como substituta.
- Semana fecha o mês: use a rota da API; o importador XLSX não produz os consolidados mensais.
- Pasta semanal existente sem `--force`: confirme que a reexecução é da mesma semana e execute novamente com `--force`.

## Textos generativos

- Subagente não criou a saída: verifique caminhos e fontes, corrija o envelope e repita uma vez com outro contexto limpo.
- Markdown vazio ou sem título `##`: repita uma vez fornecendo o mesmo prompt e fontes. Se falhar novamente, pare.
- Fonte necessária ausente: não permita que o agente improvise; volte à geração quantitativa.

## PDF

- Arquivos obrigatórios ausentes: apresente a lista devolvida pelo validador e gere somente as etapas correspondentes.
- Falha de ReportLab ou fonte: reinstale `requirements.txt` no interpretador selecionado e tente uma vez.
- PDF existente: a reexecução autorizada da mesma semana pode usar `--force`.

Não faça mais de uma repetição automática da mesma operação externa. Um segundo erro equivalente deve ser devolvido ao usuário com a proposta de correção.
