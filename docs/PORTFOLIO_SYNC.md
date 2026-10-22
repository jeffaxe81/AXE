# AXE Delivery Hub — sincronização automática

## Frequências

- **15 segundos:** páginas index.html e qualidade.html consultam o arquivo público portfolio-status.json enquanto a guia estiver ativa. Uma guia suspensa é sincronizada ao voltar.
- **Aproximadamente 5 minutos:** o GitHub Actions do repositório AXE consulta os nove repositórios públicos e grava um novo JSON na branch gh-pages.
- Agendamentos do GitHub podem atrasar e a implantação do Pages pode levar mais tempo. O site avisa quando a coleta está há mais de 20 minutos sem atualização.
- **15 segundos não significa dados novos a cada 15 segundos.** O navegador checa a origem; novas evidências dependem da coleta agendada e da publicação.

## Ativação e operação

1. Verifique Settings → Actions → General → Workflow permissions. Para publicar automaticamente na gh-pages, o token do Actions precisa de permissão de escrita no conteúdo.
2. Em Actions → Atualizar portfólio AXE, execute Run workflow na branch main para iniciar a primeira coleta, se o acionamento manual estiver habilitado.
3. Verifique o arquivo portfolio-status.json atualizado na gh-pages e, em Settings → Pages, selecione Deploy from a branch → gh-pages / (root).
4. O botão Verificar agora lê o arquivo público; ele não aciona uma nova execução do workflow.

## Fontes e interpretação

- Até 100 commits recentes na main por projeto; não constitui histórico ilimitado.
- Até 20 pull requests recentes, independentemente do período escolhido no gráfico.
- A última execução de GitHub Actions na main (se disponível).
- A presença de commits, PRs ou CI verde não altera automaticamente a situação dos marcos; percentuais são revistos com critérios de entrega/homologação.
- Falhas por fonte são indicadas em errors; valores previamente confirmados podem ser mantidos, com timestamps de verificação originais.
- Nenhuma credencial ou segredo é colocado no arquivo público; o token temporário de GitHub Actions é usado apenas durante a coleta.

## Arquivos

- main: .github/workflows/portfolio-refresh.yml e scripts/refresh_portfolio.py
- gh-pages: index.html, qualidade.html e portfolio-status.json

Se o GitHub Actions estiver desativado ou não tiver permissão para escrita, o JSON inicial permanece com generated_at nulo. A interface avisa e mantém botões para verificação manual.
