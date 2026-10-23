# Portfólio de Entregas AXE

Dashboard público hospedado no GitHub Pages para acompanhar projetos AXE, marcos documentados, histórico de entregas, próximas pendências, gráficos, amostras de PRs e status da última CI.

**Site:** https://jeffaxe81.github.io/AXE/  
**Código:** https://github.com/jeffaxe81/AXE/tree/gh-pages  
**Qualidade:** https://jeffaxe81.github.io/AXE/qualidade.html

## Publicação

O site usa a branch `gh-pages` com diretório `/(root)`. Se a publicação for desabilitada, reconfigure em [Settings → Pages](https://github.com/jeffaxe81/AXE/settings/pages), com **Deploy from a branch**, branch **gh-pages**, pasta **/(root)**.

## Seções

- **Visão geral:** resumo dos projetos e avanço de marcos.
- **Acompanhamento online:** PRs abertas (amostra de até 12 por repositório), commits recentes, execução de CI, filtros por projeto e por tipo. Escolha um projeto para solicitar consulta direta ao GitHub; a ação é limitada para não estourar a API anônima.
- **Versões e releases:** histórico por projeto com tags do Git e GitHub Releases publicados, tipo, notas, data/primeira observação, links de origem e exportação CSV.
- **Projetos:** barras de avanço, marcos concluídos e pendentes e links aos repositórios.
- **Próximas entregas:** lista de marcos ainda pendentes, filtrável por PR aberta, última CI em falha verificada ou ausência de commit registrado há 30 dias. A lista respeita a ordem editorial do plano, sem declarar prioridade ou prazo.
- **Matriz de homologação:** quatro grupos editoriais (desenvolvimento, testes, homologação e liberação/entrega) para os nove projetos. Exibe contagem de marcos concluídos em cada grupo e CI como sinal separado, com filtros e exportação CSV.
- **Evolução:** atividade recente de commits e fotografias históricas de percentuais alterados.
- **Histórico:** commits com links de evidências.
- **Relatório:** visão consolidada, CSV e impressão/PDF pelo navegador.
- **Qualidade:** página separada com dados das PRs recentes e da última CI por repositório.

## Rastreabilidade de marcos e PRs (v3)

A seção **Rastreabilidade** associa **15 referências públicas revisadas** (issues e pull requests) a marcos definidos no `index.html`. Essas associações são cadastradas em `MILESTONE_LINKS` por índice do marco, em um literal JSON (não há associação automática por palavras parecidas). O coletor valida o cadastro e busca o status oficial no repositório de origem.

- `PR integrada`: prova de integração de código, **não** de homologação.
- `Issue aberta`: pendência ou discussão identificada, não um prazo ou impedimento automaticamente comprovado.
- `Não verificado`: a informação tem mais de 20 minutos, não existe ou houve erro na leitura. A aplicação não apresenta status antigo como atual.
- **O percentual só muda** quando o marco é revisado explicitamente no cadastro. A leitura de PR ou issue jamais conclui um marco sozinha.
- Exportação de evidências em CSV com URL pública de cada associação.

Como atualizar a lista: identifique o marco em `PROJECTS[...].milestones` usando índice começando em zero; depois insira em `MILESTONE_LINKS` um objeto como `{"crm-vendas":{"2":[{"kind":"pr","number":281}]}}` (mesclado à configuração existente, sem substituir todo o objeto). Confira título, URL, projeto e pertinência antes de publicar. O script `scripts/refresh_portfolio.py` limita e valida os vínculos; falhas preservam o dado anterior somente para auditoria e o frontend o sinaliza como não verificado.

## Matriz de homologação e liberação (v4)

A matriz `GATE_MATRIX` dentro de `index.html` classifica cada marco editorial exatamente uma vez em `dev`, `tests`, `homolog` ou `release`:

- **Desenvolvimento:** somente os marcos designados para essa etapa.
- **Testes / verificação:** somente marcos explicitamente cadastrados. O resultado da última CI aparece ao lado, mas **não** conclui os marcos.
- **Homologação:** somente marcos explícitos de homologação. Se nenhum estiver mapeado, a interface indica `Não mapeado`, nunca `Aprovado`.
- **Liberação / entrega:** apenas marcos mapeados, como autorização de produção, publicação e empacotamento. `Concluído` significa somente registro editorial da etapa, não autorização automática de produção.

A interface mantém em cada projeto seus percentuais originais de marcos e **não** cria um segundo percentual enganoso de homologação. As categorias oferecem listas de marcos concluídos/pendentes, filtros por homologação pendente, liberação pendente, última CI com falha confirmada ou ausência de homologação cadastrada. Há exportação de toda a matriz em `axe-matriz-homologacao.csv`.

O cadastro inicial da matriz cobre os nove projetos e os 50 marcos listados. Para incluir um novo marco, atualize `PROJECTS` e a classificação correspondente em `GATE_MATRIX` no mesmo commit. Testes unitários rejeitam índices duplicados, ausentes ou fora do intervalo. Um resultado de CI só é apresentado como recente se a fonte foi verificada nos últimos 20 minutos e não houve erro na coleta.

### Evidências ampliadas

A rastreabilidade agora contempla **15 vínculos**. Além dos já verificados para CRM, AXE Dispatch, AXE Voice, Gestão de Convites e Central de Alertas, foram adicionadas referências públicas para validação SIP e mídia SRTP do PABX (PRs #53/#54), para a base SIP e homologação LAB do AXE Voice (PRs #70/#76) e para a homologação diferencial do Dispatch (PR #166). PR aberta indica trabalho ainda sujeito a revisão; **não** equivale a homologação concluída.

## Controle documental de GO / NO-GO (v5)

A seção **GO / NO-GO** do site oferece uma trilha de evidências obrigatórias e um histórico de decisões por projeto. A fonte canônica é [`release-approvals.json`](https://github.com/jeffaxe81/AXE/blob/gh-pages/release-approvals.json), na branch `gh-pages`. Ela começa deliberadamente **sem aprovações** para os nove projetos. "Sem decisão registrada" **não** equivale a NO-GO formal; significa apenas ausência de um GO ou NO-GO documentado.

Os cinco critérios explícitos são:

1. `functional` — testes funcionais e de integração documentados.
2. `security` — revisão de segurança e privacidade.
3. `data` — tratamento de dados, continuidade e recuperação, quando aplicáveis.
4. `rollback` — implantação e retorno seguro, quando aplicáveis.
5. `approval` — aceite ou aprovação formal registrada.

Cada critério deve ficar como `not_recorded` com `evidence`, `note` e `verified_at` nulos, ou `verified` com URL pública do **mesmo repositório**, uma nota útil (8–400 caracteres) e data UTC `YYYY-MM-DDTHH:MM:SSZ`. Não existe aprovação implícita nem critério automaticamente concluído porque uma PR foi integrada ou um workflow passou.

### Histórico de decisões

O campo `decisions` é uma lista ordenada, inicialmente vazia, de eventos declarativos. Um evento exige todos os campos abaixo; exemplos dos tipos, não de uma aprovação real:

```json
{
  "outcome": "NO_GO",
  "reviewer": "github-reviewer",
  "recorded_at": "2026-10-23T15:40:00Z",
  "sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "reference": "https://github.com/jeffaxe81/crm-vendas/issues/159",
  "reason": "Pendentes testes de ambiente e aprovação documentada antes da liberação."
}
```

O exemplo acima é **fictício**: nunca deve ser copiado como decisão real. `reviewer` identifica um perfil declarado, não é uma assinatura criptográfica. Para decisões reais, registre quem aprovou, a evidência original e o SHA efetivo da versão avaliada. Mantenha os eventos anteriores para consulta, não os substitua.

Para aceitar `GO`, o coletor exige simultaneamente:

- os **cinco critérios** no estado `verified`, cada um com evidência pública, nota e data;
- marco(s) de **homologação e liberação** explicitamente mapeados e marcados concluídos no `GATE_MATRIX` e `PROJECTS`;
- data da decisão posterior às datas das evidências;
- responsável declarado, justificativa, URL pública do GitHub e SHA específico.

Qualquer violação interrompe a geração de um novo snapshot, preservando o snapshot anterior; a interface deve falhar para a posição **sem liberação presumida**. Uma declaração `NO_GO` explícita pode ser registrada sem essas aprovações, com justificativa e referência. O painel diferencia `GO documentado`, `NO-GO registrado`, `Sem decisão registrada` e `GO sem requisitos válidos`.

> **Atenção:** o controle é declarativo e auditável pelo histórico do GitHub, mas não constitui verificação externa independente de que o serviço foi implantado, homologado ou está em operação. Os responsáveis, as evidências e a conformidade de cada decisão ainda exigem revisão humana.

### Publicação e segurança

- Edite `release-approvals.json` em uma alteração revisada da branch do site, sem inserir credenciais, segredos, nomes de clientes privados ou dados sensíveis.
- O coletor valida o arquivo e republica a seção no próximo ciclo agendado (~5 minutos), caso os dados estejam consistentes.
- As evidências aceitas têm URLs HTTPS canônicas de `pull/N`, `issues/N`, `commit/SHA` ou `actions/runs/N` dentro do **mesmo repositório público**.
- A interface oferece filtros por situação e exportação `axe-go-no-go.csv` com critérios, evidências e última decisão.
- Os percentuais de desenvolvimento e os estados de CI/PR permanecem independentes do histórico de liberação.
- Consulte o [histórico de alterações do arquivo](https://github.com/jeffaxe81/AXE/commits/gh-pages/release-approvals.json) para rastrear revisões.

## Acompanhamento online do desenvolvimento e versionamento (v6)

A página principal oferece seções **Acompanhamento online** e **Histórico de versões e releases**, acessíveis no topo pelo menu. O painel de atividade usa dados públicos de GitHub:

- últimas **12 PRs abertas** por repositório, inclusive drafts, com título, número e data de atualização. Essa quantidade é uma **amostra**, não necessariamente o total de PRs abertas;
- até **8 commits mais recentes** por projeto exibidos na área online, com link ao commit, SHA abreviado e dia registrado;
- última execução encontrada do CI na branch \`main\`, quando disponível, com status e link;
- filtros por projeto e por tipo de atividade, exibidos dentro do próprio portfólio;
- botão **Consultar GitHub agora**, ativado ao selecionar um único projeto, que consulta diretamente commits, PRs abertas, última CI e GitHub Releases (4 chamadas sem credenciais). Aplica proteção de 90 segundos para o mesmo projeto, evitando esgotar a cota pública do GitHub.

O seletor global \`Manual / 15 s / 30 s / Online\` atualiza **a leitura do snapshot publicado**, não o próprio GitHub a cada 15 segundos. O coletor do GitHub Actions executa aproximadamente a cada 5 minutos, sujeito ao agendamento do GitHub. Se faltar informação, a interface não inventa atividades nem afirma que o projeto parou de ser desenvolvido. Uma atualização direta é temporária até a próxima coleta agendada.

### Versionamento e histórico persistente

O script em \`main/scripts/refresh_portfolio.py\` passa a consultar por repositório:

1. GitHub **Releases** públicas (últimas 20) com \`tag_name\`, data original de publicação, nome, resumo, tipo estável/pré-release e link canônico;
2. **tags Git** (últimas 30), com nome da tag e SHA de commit; sem data de lançamento inferida;
3. histórico acumulado em \`gh-pages/portfolio-status.json\`, campo \`version_history\`. Ele preserva a data \`first_seen_at\` da primeira observação e até 60 versões históricas por projeto. Uma tag passa a ser identificada como release **somente** se o GitHub Releases confirmar a publicação, preservando a primeira observação do registro.

Quando o projeto só tem uma tag, o site mostra **Tag de código**, sem declará-la versão homologada ou release lançada. Quando existe uma release oficial, mostra **Release publicada** ou **Pré-release publicada** com sua data de publicação original. Não se presumem datas para tags. Se uma tag deixa a janela das últimas 30, a entrada permanece no histórico acumulado.

A página oferece filtros de projeto/tipo e exportação \`axe-historico-de-releases.csv\`. É possível rastrear alterações do snapshot pela branch \`gh-pages\`. A automação registra as versões públicas encontradas; não altera percentuais dos marcos, estados de homologação ou GO/NO-GO.

Os dados são limitados a repositórios públicos previamente selecionados, sem tokens no HTML e com texto e links sanitizados. Novos projetos exigem inclusão explícita tanto na declaração \`PROJECTS\` quanto na lista \`REPOS\` do coletor.

## Contagem de testes executados (v7)

Na [página de qualidade](https://jeffaxe81.github.io/AXE/qualidade.html#testes) e na seção **Testes automatizados observados** da página inicial, o painel distingue **casos de teste executados**, **aprovados**, **falharam** e **ignorados**. Cada valor é associado à CI exata no GitHub Actions.

**Como funciona:** o coletor busca a última execução de CI da branch principal de cada projeto; quando há acesso aos logs, reconhece os resumos dos runners pytest, unittest, Vitest e Jest. Uma execução da CI aprovada **não é igual** a uma contagem de testes aprovada. Exemplo: a CI do AXE Dispatch de 9/10/2026 terminou com falha, embora sua suíte Vitest tenha registrado 1.366 casos aprovados. Se o log estiver indisponível, a interface mostra **Sem contagem disponível** — nunca zero inferido.

Há uma linha de base pública em [\`test-observations.json\`](https://github.com/jeffaxe81/AXE/blob/gh-pages/test-observations.json) com **contagens reais**, verificadas nos logs oficiais do GitHub Actions e vinculadas a seus IDs de execução: CRM Vendas, AXE Dispatch, AXE PABX e Central de Alertas. Esse registro também serve de alternativa quando as permissões do GitHub Actions do repositório do painel não permitirem ler os logs de outro repositório. As observações só são usadas se o **ID da CI mais recente** e sua conclusão coincidirem exatamente com o registro; em outra execução, não são reutilizadas.

A soma histórica em \`portfolio-status.json\`, campo \`test_history\`, inclui somente **execuções distintas efetivamente observadas**, sem duplicar a mesma CI em sucessivas atualizações. Ela **não representa o total vitalício do projeto**. O snapshot retém até 100 execuções observadas por repositório. Também mantém a \`verified_at.tests\`, a última verificação e a indicação de leitura parcial quando algum job não produziu resumo ou os resultados estão incompletos.

**Limitações explícitas:** uma suíte pode ter outros testes fora dos resumos reconhecidos; a soma exibida é a **quantidade identificada**, não uma afirmação sobre todos os testes existentes no código. Os links às execuções são públicos. Quando uma nova CI é executada, o coletor tenta ler seus próprios resumos. Se a API não permitir coletá-los e ainda não houver evidência revisada vinculada ao novo ID, o sistema **não transfere** a contagem antiga para a CI nova. Para exportar as linhas verificadas, use **Exportar testes CSV** na página de qualidade.

## Classificação de testes e evidência por release (v8)

O painel [Qualidade → Testes](https://jeffaxe81.github.io/AXE/qualidade.html#categorias) passa a distinguir **unitários, integração, ponta a ponta, segurança** e **não classificados**. A contagem por categoria só é exibida quando a soma dos três resultados (`passed`, `failed`, `skipped`) concilia exatamente com os totais observados da CI.

**Classificação baseada nas evidências:** a linha de base em `test-observations.json` marca `unittest Python` como `unit` e `Playwright end-to-end` como `e2e`. As demais suítes são mantidas em `unclassified`, porque nomes como `pytest`, `Vitest` ou `API` não comprovam por si sós o tipo de teste. A ausência de casos classificados em segurança/integração não prova que esses testes não existem ou que não foram executados. A manutenção do campo `category` é **editorial, revisada e explícita**; o coletor rejeita categorias desconhecidas e somas incorretas.

Para cada execução com resumo reconhecido, o snapshot publica `tests.categories`, `tests.head_sha` e preserva o `test_history` por `run_id`, atualizando o registro da mesma CI sem duplicar a quantidade acumulada. Se o sistema conseguir ler os logs automaticamente mas não houver documentação explícita da categoria, todo o resultado fica em `unclassified`. `head_sha` vem da execução registrada no GitHub Actions.

A seção **Validação por release** lista GitHub Releases publicadas e as quantidades de casos só quando `test_history[].head_sha` é idêntico ao `version_history[].sha` daquela release. Se não há igualdade exata, mostra **“Não vinculados por SHA”**, sem aproveitar a última CI ou assumir que uma execução anterior validou aquela versão. O histórico é apenas o de execuções observadas pelo sistema, não um inventário completo nem comprovação de homologação ou aprovação GO.

## Avanço na última hora (v9)

O painel [Última hora](https://jeffaxe81.github.io/AXE/#ultima-hora) mostra **quantos pontos percentuais (p.p.) cada projeto e o portfólio avançaram** em marcos concluídos durante aproximadamente uma hora, além do número de marcos modificados e da quantidade de projetos que avançaram. A informação também aparece nos cartões dos projetos e no CSV de marcos.

### Cálculo e confiabilidade

- `progress_samples` conserva fotografias datadas do progresso editorial por projeto (até 600 registros/48 horas), sem criar datas retroativas.
- `progress_hourly` compara a fotografia atual com a observação mais recente de pelo menos 60 minutos antes e no máximo 80 minutos de distância. Sem essa base, mostra **“Aguardando 1 hora de medições”**, nunca zero presumido.
- Cada percentual = 100 × marcos concluídos / marcos cadastrados. O **avanço é a diferença em pontos percentuais**, não a variação percentual relativa. O consolidado divide a soma dos marcos concluídos pela soma dos totais, sem fazer média simples dos projetos.
- O período e os percentuais anterior/atual são exibidos. Se um marco for reaberto, o valor pode ficar negativo. Se o snapshot tiver mais de 20 minutos, os indicadores passam a “Medição antiga”.
- Após uma hora completa de medições válidas, **0 p.p.** indica que nenhum marco cadastrado mudou nesse período.
- A exportação de marcos inclui `Avanco_ultima_hora_pp`, `Marcos_ultima_hora` e `Medicao_ultima_hora`, deixando vazios os campos de variação sem comparação confiável.

Este indicador acompanha os **marcos editoriais de entrega**, não o volume de código, PRs, testes, homologação ou autorização GO/NO-GO. Nem um commit nem uma CI bem-sucedida alteram automaticamente a conclusão de um marco.

## Comparativo 1h, 6h, 24h e atividade pública (v10)

A seção [Avanço e atividade recente](https://jeffaxe81.github.io/AXE/#ultima-hora) dispõe de seletor de período **última hora, últimas seis horas, últimas 24 horas**.

### Avanço comprovável de marcos

O coletor publica `progress_windows` com chaves `60`, `360` e `1440` (minutos), calculado sobre `progress_samples`. Para cada período, exige uma fotografia anterior **pelo menos** N minutos antes e **no máximo** N+20 minutos antes; se a primeira medição ainda não existe ou o GitHub Actions ficou muito tempo sem coletar, o quadro mostra **sem histórico suficiente** e não finge zero. O indicador de 1h mantém `progress_hourly` por compatibilidade. Cada cartão exibe a diferença entre percentuais anteriores e atuais, em **pontos percentuais** (p.p.), o saldo dos marcos e a hora efetivamente observada. Com snapshot mais antigo que 20 minutos, esconde os números como obsoletos.

### Atividade de desenvolvimento — separada do avanço

Na mesma seção, o coletor reúne *eventos públicos*, incluindo a hora original de cada commit na `main` e os horários de atualização das últimas 20 PRs (abertas, fechadas ou mescladas) na ordem de atualização. A área de atividade apresenta por período:

- **Commits na main**, dos últimos 100 commits consultados por repositório, respeitando o horário UTC original.
- **PRs atualizadas**, das últimas 20 PRs consultadas, independentemente de estarem abertas ou mescladas; atualizar uma PR não prova que foi implementada, revisada ou integrada.
- **Última CI recente**, que indica se a execução de CI mais recente retornada na branch `main` foi atualizada no período. Não é o total de CIs executadas.

Os indicadores mostram disponibilidade por repositório e deixam como `—` fontes sem coleta recente. Se a janela das últimas 100 commits ou 20 PRs estiver cheia e o evento mais antigo ainda estiver dentro do período, o cartão do projeto mostra **≥N**, pois o número real pode ser maior. As atividades não alteram os percentuais dos marcos, nem significam GO / homologação.

**Precisão:** os dados de atividade são exibidos com base na última coleta da API, com verificação de hora UTC e atualização nos intervalos de snapshot. O seletor de 15/30 segundos da interface consulta a fotografia publicada, não solicita a API pública inteira nesse ritmo.

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
