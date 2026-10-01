# ADR-005 — Medição-como-spec e guards-catraca desde o dia 0

**Status:** modelo (adote com data e dono no seu projeto)

## Contexto

No projeto-origem (o app do ciclo 2026), qualidade visual/estrutural era verificada por olho e
por relato. Resultado acumulado: 6.606 cores hardcoded, 60 rotas estourando, navegação
93% hardcoded e uma PWA que não instalava — cada eixo custou um ciclo de remediação de
semanas com auditoria adversarial. As duas causas-raiz: (1) não havia MEDIÇÃO
reproduzível (opinião no lugar de número), (2) não havia GUARD impedindo a dívida nova.

## Decisão

1. **Toda propriedade de qualidade que importa vira medição executável** (spec/script),
   com prova de reprodutibilidade (assinatura/hash de duas execuções idênticas) — nunca
   checklist manual.
2. **Todo padrão do projeto vira guard no CI com baseline ZERO** e catraca bidirecional
   (não sobe; ao descer, a baseline desce junto obrigatoriamente).
3. **Asserções provam o estado FINAL, com alvo que falharia sem o fix** — teste verde
   que aceita estado transitório ou alvo que não exercita a regra é considerado
   não-escrito (lição: SW "verde" que nunca instalou; asserção de cache vácua).
4. **Fixtures densos e válidos por construção**: gerador com DV/regra real para
   documentos; seeds idempotentes com guard de banco local; medição nunca em tela vazia.
5. **O olho decide estética num GATE explícito do dono; números decidem o resto.**

## Consequências

- (+) Dívida estrutural não nasce; PR ruim fica vermelho de graça.
- (+) Refactor barato: a varredura diz em minutos se algo estourou em algum viewport.
- (+) Auditoria (humana ou de IA) tem o que re-executar em vez de o que acreditar.
- (−) Custo fixo de manter a matriz de rotas/pares/regras atualizada (minutos por
  feature) — aceito; é ordens de magnitude menor que a remediação.
- (−) Guards têm limitações declaradas no próprio cabeçalho — onde não
  alcançam, screenshot nos 2 temas é o fallback documentado.
