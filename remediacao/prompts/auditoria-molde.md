# Prompt-molde — AUDITORIA de uma entrega (a própria sessão auditora segue este roteiro)

> Não é um prompt para colar: é o ROTEIRO que a sessão planejadora/auditora executa ao
> receber um handoff. Vem das 12 auditorias reais do ciclo 2026.

## 1. Antes de tudo

- [ ] Ambiente saudável: servidores de pé (curl), banco local, seeds aplicados.
      (128 vermelhos por connection-refused já foram pareceres desperdiçados.)
- [ ] `git log` + `git status`: commits atômicos? árvore limpa COMO declarado?
      (Já pegamos "árvore limpa" com artefato de baseline sobrescrito sem commit.)
- [ ] Ler o handoff INTEIRO — inclusive (principalmente) as ressalvas.

## 2. Re-executar as provas — nunca aceitar o relato

- [ ] A prova de reprodutibilidade do eixo (varredura/hash/assinatura) — execução
      INDEPENDENTE, com identificador de execução PRÓPRIO quando os verificadores permitirem
      (o consolidador recusa execuções misturadas — com identificador próprio, essa recusa
      trabalha A FAVOR da auditoria).
- [ ] Gates estáticos (tsc, guards, validadores) re-executados.
- [ ] Suíte E2E pertinente re-executada. Falhou? Re-rodar ISOLADO antes de acusar
      (cold-compile, carga e state-leakage são réus conhecidos) — mas 2 falhas
      consecutivas isoladas = investigação de verdade, com trace/screenshot.
- [ ] Provas com premissa: o teste verde assere o ESTADO FINAL (activated, não
      installing)? A asserção negativa é exercitada com alvo que FALHARIA sem o fix?
      (Um SW que nunca instalou passou por 2 auditorias com spec verde.)

## 3. Subagentes adversariais (1 a 3, com mandato de DERRUBAR)

Prompt-tipo: "Reconte <números> dos dados CRUS (nunca dos totais prontos); diff linha a
linha contra <baseline>; leia o diff dos commits atrás de mudança de comportamento
escondida / cor hardcoded / <violação do eixo>; conteste, não confirme; evidência
arquivo:linha; formato ACHADOS numerados CRÍTICO/MÉDIO/BAIXO/OK-VERIFICADO + veredito."

Regra de ouro: dê ao subagente a permissão explícita de estar CERTO contra você — os
melhores achados do ciclo contrariaram a expectativa da auditoria (ranking que mudou,
regex da auditoria que estava errado).

## 4. Verificações que sempre pagam

- [ ] Plantar violação sintética e ver o guard/detector ACUSAR (e restaurar).
- [ ] Amostrar visualmente 2-3 screenshots entregues (já pegamos screenshot de 404 e
      screenshot da página errada servindo de "prova de aceite").
- [ ] Conferir alegação contra artefato: contagens declaradas vs. disco; "texto
      corrigido" vs. o texto de fato.
- [ ] Dado usado na medição: denso ou vazio? (Placar de módulo vazio é piso, não teto.)

## 5. Parecer

§ numerado no HANDOFF com: provas re-executadas (com resultado), achados em tabela
(# / achado / evidência / correção exigida), decisões da auditoria (perguntas abertas
respondidas), e veredito explícito: APROVADO / APROVADO COM CONDIÇÕES (mini-rodada
nomeada: A1, B2, M1…) / REPROVADO. Condição sem dono e sem critério de verificação
não é condição — é desejo.

## 6. Depois

Mini-rodada volta → verificar SÓ as condições (proporcional), mas com pelo menos uma
prova de regressão do todo. Registrar lições novas no METODO.md do kit.
