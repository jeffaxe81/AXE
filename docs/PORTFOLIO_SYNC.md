## Opções de atualização (interface)

O seletor está presente tanto no portfólio quanto em "PRs & CI", usa a mesma preferência salva no navegador (`localStorage`) e oferece:

| Opção | Funcionamento |
| --- | --- |
| **Manual** | Não agenda consultas. Use **Verificar agora** para ler o snapshot; na página de qualidade, **Consultar API manualmente** permite verificar diretamente o GitHub. |
| **Automático · 15 s** | A página lê o snapshot a cada 15 segundos enquanto estiver visível. |
| **Automático · 30 s** | A página lê o snapshot a cada 30 segundos enquanto estiver visível. |
| **Online · acompanhar** | Lê o snapshot a cada 15 segundos e imediatamente ao retornar à aba ou recuperar a conexão. Não é um fluxo instantâneo do servidor. |

A alteração de modo cancela o timer anterior (não acumula vários agendamentos); o botão **Verificar agora** continua disponível em todos os modos. Caso não haja internet, os dados exibidos anteriormente são preservados e a verificação retorna quando a conexão se restabelece. Guias em segundo plano não executam as checagens periodicamente.

**Importante:** os 15/30 segundos e o modo Online são intervalos de **consulta da página**. A coleta de novos dados dos repositórios continua agendada no GitHub Actions a cada aproximadamente **cinco minutos** e pode atrasar por limitações do GitHub ou de cache. Para atualização realmente instantânea seria necessário um serviço de backend/webhooks, fora da arquitetura estática atual.


# AXE Delivery Hub — sincronização automática

## Frequências

- **15 segundos:** páginas index.html e qualidade.html consultam o arquivo bruto público da branch gh-pages pelo domínio raw.githubusercontent.com, com cache-busting. Isso dispensa novos builds do Pages apenas para atualizar o JSON enquanto a guia estiver ativa. Uma guia suspensa é sincronizada ao voltar.
- **Aproximadamente 5 minutos:** o GitHub Actions do repositório AXE consulta os nove repositórios públicos e grava um novo JSON na branch gh-pages; o gatilho de push em main roda o coletor quando código, testes ou workflow são modificados.
- Agendamentos do GitHub podem atrasar e a implantação do Pages pode levar mais tempo. O site avisa quando a coleta está há mais de 20 minutos sem atualização.
- **15 segundos não significa dados novos a cada 15 segundos.** O navegador checa a origem; novas evidências dependem da coleta agendada e da publicação.

## Ativação e operação

1. Verifique Settings → Actions → General → Workflow permissions. Para publicar automaticamente na gh-pages, o token do Actions precisa de permissão de escrita no conteúdo.
2. Em Actions → Atualizar portfólio AXE, use Run workflow na branch main para uma coleta sob demanda, se o acionamento manual estiver habilitado. O workflow também executa por mudanças no código na main e por cron `3-58/5 * * * *` (UTC, aprox. a cada 5 minutos).
3. Verifique o arquivo portfolio-status.json atualizado na gh-pages e, em Settings → Pages, confirme Deploy from a branch → gh-pages / (root), para servir as páginas HTML. O JSON atualizado é lido diretamente do GitHub Raw, independentemente da recompilação do Pages.
4. O botão Verificar agora lê o arquivo público; ele não aciona uma nova execução do workflow.

## Fontes e interpretação

- Até 100 commits recentes na main por projeto; não constitui histórico ilimitado.
- Até 20 pull requests recentes, independentemente do período escolhido no gráfico.
- A última execução de GitHub Actions na main (se disponível).
- A presença de commits, PRs ou CI verde não altera automaticamente a situação dos marcos; percentuais são revistos com critérios de entrega/homologação.
- Falhas por fonte são indicadas em errors; valores previamente confirmados podem ser mantidos, com timestamps de verificação originais.
- Nenhuma credencial ou segredo é colocado no arquivo público; o token temporário de GitHub Actions é usado apenas durante a coleta.


## Histórico real dos percentuais

- O coletor extrai apenas listas literais de marcos de `gh-pages/index.html` (não executa JavaScript). A estrutura é validada por testes; um formato incompatível interrompe a publicação para evitar números inventados.
- O arquivo público `portfolio-status.json` contém `progress` e `progress_history`. Uma nova fotografia é gravada **somente quando** o total ou a quantidade concluída de algum projeto muda.
- A linha de base revisada em **22/10/2026** possui 9 projetos e 30 de 50 marcos concluídos (60%). A coleta foi executada com sucesso em **22/10/2026 às 22h07, horário de Brasília**, na [execução GitHub Actions #39882141685](https://github.com/jeffaxe81/AXE/actions/runs/39882141685). O campo `generated_at` indica a coleta mais recente; não representa homologação dos projetos.
- O gráfico de evolução mostra somente os pontos históricos efetivamente registrados, sem interpolar progresso de datas antigas. O histórico tem um limite de 365 mudanças, não 365 dias.
- O site consulta o JSON a cada 15 segundos, mas **não há garantia de dado novo** nesse intervalo; o GitHub Actions é agendado a cada cinco minutos, sujeito a atrasos e às permissões do repositório.

## Saúde e confiabilidade das fontes

- Cada cartão no portfólio informa se as três fontes (commits, PRs e CI) foram verificadas, parcialmente verificadas, ficaram antigas ou falharam. O resumo mostra as contagens dos nove projetos.
- O painel de qualidade apresenta o timestamp de verificação de PRs/CI separadamente da data do evento. Na consulta direta, os horários são da requisição manual; no snapshot são as datas `verified_at` de cada campo.
- Dados são considerados antigos quando a **última confirmação de qualquer fonte necessária** tem mais de vinte minutos. Um snapshot novo não redefine a idade de um campo que falhou; valores anteriores continuam preservados, mas são identificados como antigos ou com falha.
- Sem primeira coleta, a interface mostra **não verificado**, nunca zero entregas. Não confundir verificação de API ou CI verde com homologação funcional ou GO.
- Em modo Manual, o painel não executa verificações periódicas nem consulta automaticamente a API de PRs/CI. `Verificar agora` consulta o arquivo de snapshot; os botões próprios de Histórico e Evidências fazem consultas diretas sob demanda.
- Regressões do JavaScript e dos modos Manual / 15 s / 30 s / Online são executadas por `tests/test_dashboard.cjs` (Node sem dependências), além dos testes Python dos marcos.

## Arquivos

- main: .github/workflows/portfolio-refresh.yml e scripts/refresh_portfolio.py
- gh-pages: index.html, qualidade.html e portfolio-status.json
- JSON consumido: https://raw.githubusercontent.com/jeffaxe81/AXE/gh-pages/portfolio-status.json
- O JSON agora inclui `collector.run_url` (link da execução que produziu o snapshot) e `collector.trigger` (`push`, `schedule` ou `workflow_dispatch`). Esse link aparece nos dois painéis quando validado.
- Commits enviados por GitHub Actions com GITHUB_TOKEN não disparam build de Pages; por isso o navegador consulta o JSON bruto. A CDN pode introduzir algum atraso.

Caso GitHub Actions seja desativado ou perca a permissão de escrita, as verificações continuam mostrando o último snapshot, com aviso de dados antigos após 20 minutos. A validação de continuidade depende da observação de execuções **schedule** concluídas, não apenas de execuções disparadas por **push**.

## Alerta de coleta antiga (v12 — reforço de confiabilidade)

A validação pública horária rejeita o snapshot quando `generated_at` estiver a mais de **30 minutos** do horário UTC real, ou no futuro por mais de cinco minutos. O antigo limite de duas horas deixava aparecer uma verificação verde para um portfólio desatualizado. Agora o job sinaliza falha com indicação para verificar o agendamento do coletor.

O coletor permanece agendado aproximadamente a cada cinco minutos; a execução efetiva depende do serviço GitHub Actions e pode atrasar. Uma falha de frescor **não reprova funcionalmente nenhum produto**: indica que o monitoramento não confirmou dados recentes e requer inspeção. Os testes de comportamento da página agora incluem a área V12 de referências para revisão.
