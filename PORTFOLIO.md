# Portfólio de Entregas AXE

Dashboard público hospedado no GitHub Pages para acompanhar projetos AXE, marcos documentados, histórico de entregas, próximas pendências, gráficos, amostras de PRs e status da última CI.

**Site:** https://jeffaxe81.github.io/AXE/  
**Código:** https://github.com/jeffaxe81/AXE/tree/gh-pages  
**Qualidade:** https://jeffaxe81.github.io/AXE/qualidade.html

## Publicação

O site usa a branch `gh-pages` com diretório `/(root)`. Se a publicação for desabilitada, reconfigure em [Settings → Pages](https://github.com/jeffaxe81/AXE/settings/pages), com **Deploy from a branch**, branch **gh-pages**, pasta **/(root)**.

## Seções

- **Visão geral:** resumo dos projetos e avanço de marcos.
- **Projetos:** barras de avanço, marcos concluídos e pendentes e links aos repositórios.
- **Próximas entregas:** lista de marcos ainda pendentes, filtrável por PR aberta, última CI em falha verificada ou ausência de commit registrado há 30 dias. A lista respeita a ordem editorial do plano, sem declarar prioridade ou prazo.
- **Evolução:** atividade recente de commits e fotografias históricas de percentuais alterados.
- **Histórico:** commits com links de evidências.
- **Relatório:** visão consolidada, CSV e impressão/PDF pelo navegador.
- **Qualidade:** página separada com dados das PRs recentes e da última CI por repositório.

## Atualização automática

O workflow `.github/workflows/portfolio-refresh.yml`, localizado na branch `main`, dispara a coleta agendada aproximadamente a cada **cinco minutos**. Pode ocorrer atraso por agendamento do GitHub Actions. Ele grava `portfolio-status.json` na branch `gh-pages` com dados **públicos** de commits, até 20 PRs recentes por projeto, última execução de CI na `main` e histórico de avanço de marcos.

O painel oferece **Manual**, **15 s**, **30 s** e **Online**. Esses intervalos são consultas ao snapshot publicado, **não** representam coleta em tempo real do GitHub a cada segundo. O botão de atualização manual consulta a mesma fonte. A área de fontes informa quando os dados estão antigos ou indisponíveis. Verifique a [última execução do coletor](https://github.com/jeffaxe81/AXE/actions/workflows/portfolio-refresh.yml) em caso de falha.

## Cálculo de percentuais

Edite a declaração `PROJECTS` no `index.html` da branch `gh-pages`. Cada `milestones` contém itens no formato `["Descrição", true/false]`.

```text
Avanço do projeto = 100 × marcos marcados true / marcos mapeados
```

A métrica **não** mede horas trabalhadas, esforço real, percentual do backlog completo, aceite, homologação nem prontidão para produção. A ordem da lista determina o "próximo marco listado" na seção de pendências. **Commits ou PRs não concluem marcos automaticamente.** Uma mudança de percentual é registrada no `progress_history` somente quando o próprio cadastro de marcos é revisado e a próxima coleta acontece.

## Regras para evidências e filtros

- PRs abertas: contagem limitada às **20 PRs mais recentemente atualizadas**, nunca total histórico.
- CI: considera a última execução identificada na branch `main`; uma execução concluída com sucesso não equivale a homologação do produto.
- Filtros de PR/CI da fila exigem uma leitura sem erro e verificada há no máximo **20 minutos**; sem confirmação recente, a informação é tratada como **desconhecida**, não como zero ou sucesso.
- Ausência de commits registrados há 30 dias significa apenas isso: **não é atraso**.
- Projetos e marcos publicados são uma seleção curada; repositórios privados e informações confidenciais ficam de fora.

## Testes

O pipeline de `main` roda:

```bash
python3 -m unittest discover -s tests -p 'test_portfolio.py' -v
node tests/test_dashboard.cjs path/to/gh-pages/index.html path/to/gh-pages/qualidade.html
```

A branch `gh-pages` também possui testes e uma validação dedicada de páginas. O site é totalmente estático, sem servidor próprio, autenticação, tokens ou credenciais expostas ao navegador.

## Segurança e privacidade

Não incluir no HTML, JSON público ou histórico IPs internos, chaves, certificados privados, credenciais SIP, nomes de clientes não públicos ou dados pessoais. Todos os links gerados usam repositórios públicos conhecidos e URLs do GitHub.
