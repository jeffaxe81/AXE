# AXE Delivery Hub — sincronização automática

## Frequências

- **15 segundos:** páginas index.html e qualidade.html consultam o arquivo bruto público da branch gh-pages pelo domínio raw.githubusercontent.com, com cache-busting. Isso dispensa novos builds do Pages apenas para atualizar o JSON enquanto a guia estiver ativa. Uma guia suspensa é sincronizada ao voltar.
- **Aproximadamente 5 minutos:** o GitHub Actions do repositório AXE consulta os nove repositórios públicos e grava um novo JSON na branch gh-pages.
- Agendamentos do GitHub podem atrasar e a implantação do Pages pode levar mais tempo. O site avisa quando a coleta está há mais de 20 minutos sem atualização.
- **15 segundos não significa dados novos a cada 15 segundos.** O navegador checa a origem; novas evidências dependem da coleta agendada e da publicação.

## Ativação e operação

1. Verifique Settings → Actions → General → Workflow permissions. Para publicar automaticamente na gh-pages, o token do Actions precisa de permissão de escrita no conteúdo.
2. Em Actions → Atualizar portfólio AXE, execute Run workflow na branch main para iniciar a primeira coleta, se o acionamento manual estiver habilitado.
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
- A linha de base revisada em **22/10/2026** possui 9 projetos e 30 de 50 marcos concluídos (60%). O campo `generated_at` permanece nulo até a primeira coleta automática bem-sucedida: a linha de base não comprova sincronização.
- O gráfico de evolução mostra somente os pontos históricos efetivamente registrados, sem interpolar progresso de datas antigas. O histórico tem um limite de 365 mudanças, não 365 dias.
- O site consulta o JSON a cada 15 segundos, mas **não há garantia de dado novo** nesse intervalo; o GitHub Actions é agendado a cada cinco minutos, sujeito a atrasos e às permissões do repositório.

## Arquivos

- main: .github/workflows/portfolio-refresh.yml e scripts/refresh_portfolio.py
- gh-pages: index.html, qualidade.html e portfolio-status.json
- JSON consumido: https://raw.githubusercontent.com/jeffaxe81/AXE/gh-pages/portfolio-status.json
- Commits enviados por GitHub Actions com GITHUB_TOKEN não disparam build de Pages; por isso o navegador consulta o JSON bruto. A CDN pode introduzir algum atraso.

Se o GitHub Actions estiver desativado ou não tiver permissão para escrita, o JSON inicial permanece com generated_at nulo. A interface avisa e mantém botões para verificação manual.
