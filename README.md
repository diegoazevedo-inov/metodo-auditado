# Método Auditado

Protocolo de desenvolvimento com agentes de codificação, no qual a arquitetura
não confia no agente. Papéis separados, auditoria medida antes de opinião,
e guards que só valem depois de terem ficado vermelhos na sua frente.

Destilado de um ciclo real de remediação e generalizado para reaplicação —
em projetos existentes e em projetos novos.

## O que ele resolve

Agente entrega código e entrega relatório. **Relato bom não é código bom.**
Já encontrei defeito de segurança em componente que o resumo do próprio
agente havia declarado conforme. Este kit é o protocolo que faz essa
diferença aparecer antes da produção, e não depois.

## As duas metades

| Metade | Para quê | Onde |
|---|---|---|
| **Remediação** | Curar um projeto existente com dívida | [remediacao/](remediacao/) |
| **Nascença** | Projeto novo já nascer certo — dívida nunca nasce | [nascenca/](nascenca/) |
| **Skills** | Empacotamento reutilizável do protocolo | [skills/](skills/) |
| **Verificadores** | Os seis guards de interface que as fases mandam rodar, cada um com a sua prova | [guards/](guards/) |

## As três ideias que sustentam o resto

**Auditoria medida antes de opinião.** Nenhuma fase começa com "acho que".
Começa com números reprodutíveis, e o número vira a manchete do plano e o
placar que as fases zeram.

**Violação sintética.** Um detector que nunca acusou na sua frente não provou
nada. Plante o defeito de propósito e confirme que o guard fica vermelho —
antes de confiar nele.

**Reproduzir a prova ≠ validar a premissa da prova.** Suíte verde e Lighthouse
verde sobre um service worker que nunca instalava: o teste aceitava estado
transitório. Endureça a asserção para o estado final antes de confiar no verde.

## Os 4 eixos

1. **Tema claro/escuro** — tokens semânticos, contraste WCAG computado, guard de paleta
2. **Fluxos contínuos de UI/UX** — navegação com contexto, filtros na URL
3. **Responsividade** — gabarito de layout, varredura como spec, catraca
4. **PWA** — cache seguro para dado vivo, SW provado, manifest theme-aware

Cada eixo traz receita de auditoria medida, fases com gate, prompts-molde para
executor e auditor, e o legado permanente — os guards e specs que ficam
impedindo a dívida de voltar.

## Por onde começar

- Projeto existente → [METODO.md](METODO.md), depois o eixo com a dívida mais dolorida
- Projeto novo → [nascenca/BOOTSTRAP.md](nascenca/BOOTSTRAP.md), antes da primeira tela
- Em qualquer caso, o [METODO.md](METODO.md) é a lei; os eixos são aplicações dela

## Resultados do ciclo de origem

De 60 rotas estourando, 6.606 cores hardcoded, navegação 93% quebrada e uma PWA
que não instalava — para zero estouro provado por assinatura, dois temas com
contraste validado, navegação com contexto e Lighthouse 100 em produção.

12 pareceres de auditoria adversarial. 3 bugs reais de produto descobertos
no caminho.

## Licença

Apache 2.0
