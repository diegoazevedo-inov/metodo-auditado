# Remediação — o protocolo em 1 página

Para curar um projeto existente num dos 4 eixos. A lei completa está em
[../METODO.md](../METODO.md); isto é o mapa de execução.

## Passo a passo

1. **Auditoria medida do eixo** (30–60 min): rode a receita de greps do eixo
   (`10-eixo-tema.md`, `20-eixo-fluxos.md`, `30-eixo-responsividade.md`,
   `40-eixo-pwa.md`, seção "Auditoria medida"). O resultado são NÚMEROS.
2. **PLAN-<ciclo>.md**: números na abertura, fases com gates, e as **decisões do dono**
   como seção própria — pergunte ANTES de começar (matriz de dispositivos? default de
   tema? offline com sync?), registre resposta com data.
3. **Prompt da fase 0** via [prompts/executor-molde.md](prompts/executor-molde.md) →
   outra sessão executa → devolve HANDOFF.
4. **Auditoria** via [prompts/auditoria-molde.md](prompts/auditoria-molde.md) →
   parecer numerado → mini-rodadas até fechar → próxima fase.
5. **Gate visual do dono** no piloto (fase 1) — sem aprovação, sem migração em massa.
6. Fases de migração por **lotes rankeados** (2–4 módulos por rodada de auditoria).
7. Ao fechar o ciclo: **guards no CI**, PADROES atualizado, lições novas no METODO.md.
8. **Deploy é do dono**, sempre manual, sempre com backup antes e fumaça depois.

## Ordem recomendada entre eixos (se a dívida for geral)

1. **Tema** primeiro se há cor hardcoded em massa (é pré-requisito de qualquer UI nova).
2. **Fluxos** em paralelo ou logo após (independente de visual).
3. **Responsividade** depois do tema (o gabarito usa os tokens).
4. **PWA** por último, sempre — instalar como app uma tela que estoura é embalar defeito.

## Sinais de que o protocolo está degradando (pare e corrija)

- Handoff sem números ou sem ressalvas ("tudo verde" seco).
- Auditoria aceitando relato sem re-executar prova.
- Fase corrigindo coisa de outra fase "de passagem".
- Executor e auditor na mesma sessão "só desta vez".
- Guard com escape hatch sem comentário de justificativa.
