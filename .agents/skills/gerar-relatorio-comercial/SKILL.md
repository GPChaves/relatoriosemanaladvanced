---
name: gerar-relatorio-comercial
description: Executa o relatório semanal de desempenho comercial da Advanced Mecânica, coletando entradas manuais, obtendo dados do Kommo ou de um XLSX exportado, delegando cada texto a um subagente limpo e entregando o PDF validado. Use quando o usuário pedir para gerar, regerar ou concluir esse relatório; não use para análises comerciais avulsas sem o pipeline deste projeto.
---

# Gerar relatório comercial

Produza um relatório completo para uma semana. Preserve as entradas operacionais locais e nunca use números de outra semana para preencher lacunas.

## Preparar a execução

1. Resolva a raiz com `git rev-parse --show-toplevel`; não dependa do diretório atual nem grave caminhos absolutos nos prompts.
2. Obtenha a segunda-feira da semana em `AAAA-MM-DD`. Se não tiver sido informada, peça-a antes de prosseguir. Se essa segunda-feira estiver no futuro no fuso `America/Sao_Paulo`, não colete dados nem execute o pipeline; informe a primeira data em que a semana poderá ser tratada como parcial.
3. Se `load_workspace_dependencies` estiver disponível, use-o para localizar Python. Caso contrário, procure `python` ou `py`. Use o mesmo interpretador em todos os comandos.
4. Verifique sem revelar valores se `env.txt` contém `KOMMO_TOKEN` e `KOMMO_BASE_URL`. A rota XLSX não precisa consultar a API.
5. Mantenha um plano curto com coleta, dados quantitativos, subagentes, validação e PDF.

## Coletar entradas manuais

Leia [references/entradas-manuais.md](references/entradas-manuais.md). Verifique primeiro se a semana já possui um CSV válido de tempo de resposta, exatamente três fontes válidas de atendimento e os metadados de cliente e lead de cada caso. Cada caso pode ser uma imagem PNG/JPG ou uma transcrição TXT. Ofereça também a avaliação do gestor, deixando explícito que ela é opcional e que sua ausência não interrompe a execução.

Peça em uma única mensagem somente o que estiver ausente. Diga explicitamente que a skill está pausando para aguardar as entradas. Quando o usuário responder, salve os dados nos caminhos semanais e valide novamente antes de consultar a API ou processar o XLSX. Confirme com `git check-ignore` que cada entrada salva está ignorada; se não estiver, pare e corrija o `.gitignore` antes de continuar.

Não sobrescreva uma entrada manual existente com conteúdo diferente sem avisar. Não coloque entradas manuais, outputs, imagens, transcrições ou credenciais no Git.

## Gerar os CSVs

Prefira a API quando as credenciais estiverem configuradas e o usuário não tiver fornecido um XLSX:

```powershell
python relatorio.py --week-start AAAA-MM-DD --validate-only
python relatorio.py --week-start AAAA-MM-DD --force
```

Quando o usuário fornecer um export do Kommo, use:

```powershell
python importar_export_kommo.py --source ARQUIVO.xlsx --week-start AAAA-MM-DD --force
```

Passe `--pipeline-name` somente quando o usuário indicar um nome diferente. A rota XLSX não suporta uma semana de fechamento mensal; nesse caso, explique e use a API após confirmar que as credenciais existem.

Capture código de saída, `stdout` e `stderr`. Em caso de erro, pare a etapa, leia [references/diagnostico-erros.md](references/diagnostico-erros.md), devolva a mensagem útil e proponha uma correção. Não gere textos com CSVs incompletos.

Na rota da API, confirme que os indicadores de conversão, etapas e perdas usam eventos `lead_status_changed` cuja etapa de destino é `Serviço iniciado` ou `Perdido`. A data do evento define a semana; se o mesmo lead tiver mais de uma transição terminal na mesma semana, somente a última entra no indicador e todas permanecem auditáveis em `10_eventos_fechamento.csv`. Não use `closed_at` para reconciliar reaberturas.

Para os leads criados nas duas semanas comparadas, obtenha os contatos vinculados e classifique como `cliente retorno` todo lead cujo contato já possua outro lead com `created_at` anterior. Use IDs estruturais de contato e lead; nunca compare nome ou telefone. Retornos são um subconjunto dos novos leads e devem aparecer no total e por consultor em `07_novos_leads_semana.csv`.

Para qualquer indicador atribuído a um consultor, use exclusivamente o `responsible_user_id` nativo do lead e resolva o nome pela extração de usuários da Kommo. Não procure o campo personalizado `Usuário responsável` e não use `created_by`, `updated_by`, o autor da mudança de etapa nem o usuário que preencheu a ficha. Remova de Milena e Vitor qualquer sufixo iniciado por `Advanced Mecânica` ou `Advanced Mecanica`, deixando apenas `Milena` e `Vitor`. Trate `Advanced Mecânica` como conta administradora, nunca como consultor; seus leads ficam em `Sem usuário responsável`. ID ausente, inválido ou sem usuário correspondente também deve aparecer como `Sem usuário responsável`.

Na rota XLSX, exija `Lead usuário responsável`, uma coluna estável de ID do contato e uma única coluna de data de fechamento entre os nomes aceitos pelo importador. O export deve conter o histórico necessário para localizar leads anteriores do mesmo contato; caso contrário, explique que a contagem de retornos exige a rota da API. Como o XLSX é uma fotografia sem histórico de transições, registre a metodologia de fechamento como aproximação baseada na data de fechamento e na etapa terminal atual; nunca substitua essa data por `Última modificação`.

Depois da geração, compare os nomes de `04_conversao_responsavel.csv` com `09_tempo_medio_resposta.csv` apenas para detectar rótulos incompatíveis no relatório. Se algum consultor não tiver uma linha comparável, pause e peça a correção; não associe nomes por aproximação e não altere a atribuição vinda do `responsible_user_id`.

## Gerar os textos em contextos limpos

Leia [references/subagentes-generativos.md](references/subagentes-generativos.md) e `prompts/generativos/manifest.json`.

Prepare os atendimentos:

```powershell
python processar_atendimentos.py prepare --week-start AAAA-MM-DD
```

Use `collaboration.spawn_agent` com `fork_turns="none"` para cada texto. Primeiro crie três agentes isolados, um por fonte de atendimento. Para PNG/JPG, forneça a imagem; para TXT, forneça somente a transcrição. Forneça também apenas os metadados daquele caso. A análise individual deve começar com `## Atendimento — NOME DO CLIENTE — Lead NÚMERO`. Depois crie um agente limpo para a consolidação qualitativa, preservando esses títulos. Finalize e valide os hashes:

```powershell
python processar_atendimentos.py finalize --week-start AAAA-MM-DD
python processar_atendimentos.py validate --week-start AAAA-MM-DD
```

Quando existir `entradas_manuais/avaliacao_gestor/AAAA-MM-DD/avaliacao.md`, não a envie aos agentes individuais. Envie-a ao agente de consolidação dos atendimentos e somente aos itens semanais marcados com `manager_context: true` no manifesto. Ela deve orientar a análise sem ser copiada, citada ou revelada no relatório; os dados prevalecem em caso de conflito.

Em seguida, crie um agente limpo para cada item semanal do manifesto. Crie o agente mensal somente quando os CSVs mensais tiverem sido gerados. Nunca escreva um texto generativo no agente principal e nunca forneça a um agente fontes que não estejam declaradas para a seção.

Espere todos os agentes, confira que cada saída é UTF-8, não vazia e começa com `## `. Repita uma falha no máximo uma vez em outro contexto limpo.

Todo texto entregue deve soar como análise autoral do gestor. Não permita menções a arquivos internos, CSV, Markdown, coleta manual, agentes, inteligência artificial, automação, scripts ou APIs. Antes de gerar o PDF, execute o validador e corrija qualquer saída que exponha esses bastidores; não apenas remova a frase isolada se isso prejudicar o sentido.

Mantenha os textos curtos e leves. Prefira tabelas Markdown para comparações repetitivas e use a prosa somente para interpretação, decisão e ressalvas indispensáveis. Na seção `Diferenças entre consultores`, não analise tempo de resposta e não inclua o bloco `Limites de comparação`.

## Gerar e entregar o PDF

Valide antes de gerar:

```powershell
python gerar_relatorio_final.py --week-start AAAA-MM-DD --validate-only
python gerar_relatorio_final.py --week-start AAAA-MM-DD --force
```

Confirme que `outputs/AAAA/AAAA-MM-DD/relatorio_desempenho_final.pdf` existe e não está vazio. Responda com um link Markdown para o caminho local absoluto do PDF e um resumo curto das fontes usadas, da situação da semana e de qualquer limitação registrada.

Não faça commit, push, envio externo ou exclusão de outras semanas como parte desta skill.
