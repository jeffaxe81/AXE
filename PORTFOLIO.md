# Portfólio de Entregas AXE

Painel estático, responsivo e sem backend para apresentar os projetos públicos, marcos acompanhados, percentual de conclusão dos marcos e histórico de commits com links para evidências.

## Publicação no GitHub Pages

1. Abra [Settings → Pages](https://github.com/jeffaxe81/AXE/settings/pages).
2. Em **Build and deployment**, selecione **Deploy from a branch**.
3. Em Branch, escolha **gh-pages**, diretório **/(root)** e clique em **Save**.
4. Depois que o GitHub finalizar a implantação, o endereço esperado será **https://jeffaxe81.github.io/AXE/**.

> Criar a branch não habilita o Pages automaticamente em todos os repositórios. Confirme o endereço em Settings → Pages antes de compartilhar.

## Como atualizar

Edite o arquivo `index.html` nesta branch. No bloco JavaScript `PROJECTS`, cada projeto possui:
- `milestones`: pares `["Descrição do marco", true/false]`; o valor `true` significa marco documentado como concluído.
- `history`: pares de data, descrição e SHA de commits públicos.
- `updated`: data da atividade indicada no cartão.

O percentual de cada cartão é calculado com a fórmula:
`100 × número de marcos concluídos / número de marcos mapeados`.

**Interpretação:** percentual de **marcos escolhidos para monitoramento**, não de esforço executado, backlog total, estabilidade, aceite, SLA ou homologação de produção. O percentual consolidado é ponderado pela quantidade de marcos monitorados em cada projeto.

## Privacidade e fontes

Somente repositórios **públicos** são listados. Não cadastrar credenciais, IPs internos, dados de clientes, incidentes, segredos ou informações restritas no painel. Cada item do histórico aponta para um commit rastreável. Dados e marcos iniciais: 22 de outubro de 2026.

## Observações

O painel não tem coleta de dados, login ou chamadas de API: é inteiramente estático e pode ser usado diretamente pelo navegador. A lista inicial é editorial e pode ser expandida para outros repositórios.
