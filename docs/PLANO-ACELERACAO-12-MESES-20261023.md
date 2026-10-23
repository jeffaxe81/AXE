# Plano de aceleração — horizonte de 12 meses

Data-base: 2026-10-23. **Planejamento, não evidência de execução.**

## Regras de medição
- Progresso = critérios de aceite comprovados / critérios previstos; sem estimar porcentagens sem evidências.
- Separar: planejado, implementado, testes automáticos aprovados, integrado, publicado e homologado.
- Registrar por entrega: repositório, issue/PR, commit, workflow, testes executados, resultado e bloqueio.
- Não fazer merge de PR draft com validação real pendente; não declarar GO operacional a partir de CI isolada.

## Ondas de execução acelerada
| Onda | Frente | Entregáveis e critério de aceite |
|---|---|---|
| 1 | Portfólio AXE | Release timeline, histórico de testes e métricas 1h/6h/24h com fonte GitHub verificável; publicação testada |
| 1 | CRM | Validar PR #296: CI no SHA exato, isolamento RLS, no-store, CSV seguro e compatibilidade com backup |
| 1 | Dispatch | Validar PR #180 em MySQL 8.4 descartável, isolamento tenant e proibição de replay/chamadas externas |
| 2 | AXE Voice | UI compacta, seleção independente de campainha e áudio, testes unitários e integração SIP |
| 2 | AXE PABX | Ramais, troncos, roteamento, CDR, testes de segurança e recuperação |
| 3 | Integração | API de status com cache e proteção de credenciais; IA Gemini apenas por backend autenticado |
| 4 | Homologação | Testes ponta a ponta, backup/restore, carga, acessibilidade, documentação e decisão GO por projeto |

## Próximos checkpoints
1. Conferir publicação pública do painel e guardar evidência de smoke.
2. Conferir checks dos HEADs de CRM #296 e Dispatch #180.
3. Criar backlog de tarefas pequenas com critérios de aceite e testes.
4. Atualizar o painel somente com métricas verificadas.

**Limite:** antecipar planejamento em 12 meses não equivale a executar 12 meses de trabalho, nem autoriza pular homologação.
