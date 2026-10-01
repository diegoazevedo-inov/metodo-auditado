# O MÉTODO — transversal aos 4 eixos

O que fez a jornada do app do ciclo 2026 funcionar não foi nenhuma técnica de CSS ou de service
worker — foi o protocolo em volta. Este documento é a lei; os eixos são aplicações dela.

---

## 1. Os três papéis (nunca na mesma sessão)

| Papel | Faz | Nunca faz |
|---|---|---|
| **Planejador/Auditor** | Auditoria medida inicial, PLAN com fases e gates, prompts do executor, auditoria adversarial de cada entrega, pareceres numerados | Implementar o que vai auditar |
| **Executor** (outra sessão) | Implementa UMA fase por vez, entrega HANDOFF honesto com números medidos e ressalvas, commits atômicos | Auto-auditar-se; deployar; sair do escopo da fase |
| **Dono (humano)** | Decisões de produto nomeadas no PLAN, gate visual do piloto, ordem de deploy | Ser surpreendido: toda decisão dele é registrada com data |

A regra de ouro da separação: **quem escreve a prova não é quem a confere**. Toda entrega
volta para auditoria com re-execução independente — e a auditoria também erra (ver §5),
por isso o executor pode e deve refutar com prova.

## 2. Auditoria medida ANTES de opinar

Nenhuma fase começa com opinião. Começa com números que qualquer um pode reproduzir:

- grep/scan quantitativo (ex.: "34 de 85 páginas sem NENHUMA classe responsiva", "6.606
  cores hardcoded", "voltar hardcoded em 93% das telas") — o número vira a manchete do PLAN;
- os números definem o RANKING de ataque (pior primeiro) e o PLACAR que as fases zeram;
- instrumentação vira spec permanente (varredura multi-viewport, amostrador de contraste)
  — a medição sobrevive à fase e vira gate.

## 3. A anatomia de um ciclo (o esqueleto que se repete)

```
FASE 0 — instrumentar e medir     → baseline REPRODUZÍVEL (prova por assinatura/hash)
FASE 1 — gabarito + piloto        → 2 telas exemplares + GATE VISUAL do dono
FASE 2 — migração em massa        → por lotes rankeados; aceite = placar do lote em zero
FASE 3 — o eixo "premium" (PWA…)  → só sobre base sólida
```

Regras que valem em toda fase:

- **Baseline congela por prova**: duas execuções independentes com resultado idêntico
  (assinatura sha256 do CONJUNTO de defeitos — sem pixels, sem timestamps, sem texto de
  dado vivo, que muda entre dias). Jitter não se mascara: caça-se a fonte na origem.
- **Piloto com gate**: nada de migração em massa antes de o dono aprovar 2 telas de
  verdade (1 boa + 1 péssima) nos viewports/temas reais.
- **Escopo por fase é lei**: fase de medição NÃO corrige; fase de layout NÃO muda
  comportamento (handlers movidos verbatim; diff só de className é auditável).
- **Componente compartilhado tocado = prova por varredura completa**, não por opinião.
- **Guard-catraca ao final**: trava o que existe (baseline de dívida), recusa o que for
  novo, e trava NOS DOIS SENTIDOS (dívida paga rebaixa a baseline obrigatoriamente —
  senão a folga fica e alguém re-sobe sem alarme).
- **Seeds densos**: medir tela vazia é medir nada. Fixture idempotente, com guard de
  banco local e kill-switch. "O placar do módulo vazio é PISO, não teto."

## 4. A auditoria adversarial (o que "auditar" significa aqui)

1. **Re-executar as provas** — não ler o relato: rodar a suíte, a varredura, o hash.
   Ambiente saudável ANTES (servidores de pé — sim, já erramos isso; ver §5).
2. **Subagentes adversariais com mandato de derrubar**: recontar números dos dados CRUS
   (nunca dos totais prontos), diff linha a linha contra a baseline, ler o diff de código
   inteiro atrás de mudança de comportamento escondida.
3. **Plantar violação sintética** para provar que o detector/guard ACUSA (um detector que
   nunca ficou vermelho na sua frente não provou nada).
4. **Parecer numerado com condições explícitas** (aprovado-com-condições é o desfecho
   normal; reprovação seca é rara quando o protocolo roda).
5. **Mini-rodadas de correção** até fechar — pequenas, nomeadas (A1, B2, M1…), cada uma
   re-verificada.

## 5. Lições codificadas (pagas com erro real — não repita)

1. **Exit code real**: `cmd | tail` mascara o exit; use `PIPESTATUS[0]` ou log-em-arquivo.
   (Escondeu 11 falhas de Playwright uma vez.)
2. **Nunca `build`/`prisma generate` com suíte E2E rodando** — o watcher recompila no
   meio e o vermelho mente.
3. **UMA varredura por vez** — Playwright paralelo no mesmo servidor/`test-results`
   colide e derruba viewports (aconteceu com a própria auditoria).
4. **Servidores de pé antes de QUALQUER suíte** — 128 vermelhos por connection-refused
   já assinaram esse item.
5. **Gates computados > olho**: um CTA com contraste 2,94:1 foi aprovado visualmente;
   o validador que faltava pegou depois. O olho aprova estética; o gate aprova número.
6. **Reproduzir a prova ≠ validar a premissa da prova**: a auditoria re-executou spec e
   Lighthouse verdes sobre um SW que NUNCA instalava — o teste aceitava estado transitório.
   Endureça a asserção (estado FINAL: `activated` + `controller`) antes de confiar no verde.
7. **A auditoria também erra — e o executor refuta com prova**: um regex sugerido pela
   auditoria estava errado; o executor provou empiricamente e prevaleceu. Isso é saúde.
8. **Validação na borda tem alcance além dos POSTs**: ligar validador de payload quebra
   todo teste que DIGITA valor sintético na UI. Roteie fixtures pela mesma fonte de verdade.
9. **Medição com dado vivo não é byte-estável entre dias** (juros acumulam, textos mudam)
   — por isso a prova canônica é a assinatura sem texto/pixel, não o JSON inteiro.
10. **Dado financeiro/autenticado NUNCA em cache de SW** — inclui `/uploads` (comprovantes),
    não só `/api`; `Cache-Control: private` é IGNORADO pelo runtime caching do Workbox.
11. **Não mutar DOM que o framework possui** (metas de head do React/Next) — hydration
    error intermitente que derruba navegação é o sintoma.
12. **Honestidade no handoff é requisito, não cortesia**: ressalvas declaradas ("medido
    com portal VAZIO", "screenshots não re-tirados") foram o que permitiu à auditoria
    achar o que importava. Handoff que só conta vitória é handoff reprovado.

## 6. Documentos do protocolo

- `PLAN-<ciclo>.md` — auditoria medida, fases, decisões do dono (com data), gates.
- `HANDOFF-<ciclo>.md` — documento VIVO: executor escreve §§ de entrega, auditor escreve
  §§ de parecer, numerados e intercalados. É a memória oficial do ciclo.
- `PADROES-<eixo>.md` — o gabarito-lei do eixo (atualizado quando a fase muda a regra).
- Prompts-molde em [remediacao/prompts/](remediacao/prompts/).

## 7. Quando usar cada metade

- Projeto existente: remediação, um eixo por vez, na ordem da dor (a auditoria medida
  inicial de cada eixo — 30 min de greps — diz onde dói mais).
- Projeto novo: [nascenca/](nascenca/) inteiro ANTES da primeira tela. Custa horas;
  a alternativa custou meses (60→0 levou 4 lotes; 86 dívidas de guard levaram semanas
  para descer a 67 — no dia 0 a baseline é ZERO de graça).
