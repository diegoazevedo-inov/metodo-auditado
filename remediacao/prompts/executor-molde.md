# Prompt-molde — SESSÃO EXECUTORA de uma fase

> Preencha os `<>`. Uma fase por prompt. O molde vem dos prompts reais do ciclo 2026
> (H0…H3-A) — o que está fora de `<>` é a parte que provou funcionar; mude com critério.

```
Você é a SESSÃO EXECUTORA da fase <FASE> do ciclo <CICLO>. A auditoria será feita por
OUTRA sessão ao final. Leia INTEIROS: <PLAN do ciclo>, <PADROES do eixo> e as seções
<§§ relevantes> do <HANDOFF>. As fases <FASES FUTURAS> são PROIBIDAS nesta rodada.

## Escopo
<lista numerada e FECHADA do que esta fase entrega — item a item, com critério de pronto
por item. Inclua o que ela explicitamente NÃO faz.>

## Regras (as de sempre — não são opcionais)
- Nenhuma mudança de comportamento junto com <layout/estilo/infra> — diff de forma não
  esconde diff de lógica.
- <regra do eixo: só tokens de tema / gabarito sempre / política de cache por tipo…>
- Componente compartilhado tocado ⇒ provar por <varredura/suite> completa.
- Disciplina de ambiente: servidores atuais ANTES de qualquer suíte; exit codes reais
  (PIPESTATUS, nunca pipe mascarando); NUNCA build/generate com E2E rodando; UMA
  varredura por vez.
- Commits atômicos por unidade de entrega. NÃO deployar.

## Verificação obrigatória ANTES de devolver
<lista (a)(b)(c)… do que TEM que estar verde, com o comando de cada prova. Sempre inclua:
a medição do eixo re-executada com prova de reprodutibilidade; os gates estáticos do
projeto; a suíte E2E pertinente; screenshots quando visual.>

## Entrega
<HANDOFF>.md §<N> com: números MEDIDOS (nunca estimados), decisões tomadas com
justificativa, limitações conhecidas e RESSALVAS HONESTAS (o parecer pune omissão, não
ressalva declarada). Status final: "aguardando auditoria da <FASE>".
```

## Notas de uso

- **Escopo fechado é o que segura o executor** — "aproveitando que estou aqui" é a
  principal fonte de regressão não-auditada.
- A lista de verificação (a)(b)(c) vira o checklist do parecer do auditor — escreva-a
  pensando em quem vai conferir.
- Se a fase tem GATE VISUAL do dono, o prompt deve mandar PARAR no piloto.
