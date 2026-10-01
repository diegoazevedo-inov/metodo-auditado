# Método Auditado

Um método para desenvolver software com agentes de codificação sem depender do
que o agente diz sobre o próprio trabalho. Ele se apoia em três regras: quem
implementa não audita, nenhuma decisão é tomada sem medição, e nenhum
verificador entra em uso antes de acusar um defeito plantado de propósito.

Serve para dois casos: recuperar um projeto que já acumulou dívida técnica e
começar um projeto novo sem acumulá-la.

## O problema

Um agente de codificação entrega o código e, junto, um resumo dizendo que está
tudo certo. As duas coisas não se confundem: um resumo convincente não garante
código correto. O método existe para que a distância entre o que foi relatado
e o que foi feito apareça durante o desenvolvimento, e não em produção.

## O que tem aqui

| Parte | Para quê | Onde |
|---|---|---|
| **Remediação** | Recuperar um projeto existente: o protocolo e um roteiro por eixo | [remediacao/](remediacao/) |
| **Nascença** | Começar um projeto novo já dentro das regras: roteiro de partida e decisões de arquitetura | [nascenca/](nascenca/) |
| **Skills** | Uma skill de agente por eixo: mede a dívida e devolve o esqueleto do plano, sem corrigir nada | [skills/](skills/) |
| **Verificadores** | Os seis guards de interface que as fases mandam rodar, cada um com a sua prova | [guards/](guards/) |

## Princípios

**Quem implementa não audita.** Três papéis, nunca na mesma sessão: quem
planeja e audita, quem executa, e o dono, que decide e tem cada decisão
registrada. A auditoria não aceita o relato da entrega como prova: executa de
novo as provas. Ela também erra, e por isso o executor pode contestá-la, com
prova.

**Medir antes de opinar.** Toda fase começa por uma medição reproduzível. O
número vira a meta do plano e o placar que as fases seguintes levam a zero.

**Defeito plantado antes de confiar.** Um verificador que nunca acusou nada não
provou que funciona. Antes de usá-lo, planta-se de propósito o defeito que ele
deve pegar, e confirma-se que ele reprova.

**Prova verde não valida a premissa.** Uma suíte que passa pode estar provando a
coisa errada. Um teste que aceita um estado intermediário fica verde mesmo
quando o resultado final nunca acontece, como um service worker que nunca chega
a instalar. A asserção tem de exigir o estado final.

## Os quatro eixos

1. **Tema claro e escuro**: cores só por tokens semânticos, contraste calculado
   pela WCAG e verificador de paleta.
2. **Fluxos de navegação**: voltar sem perder o contexto, com filtros e estado
   na URL.
3. **Responsividade**: gabarito de layout, varredura em vários tamanhos de tela
   e uma catraca que impede a dívida de crescer.
4. **PWA**: cache que não guarda dado autenticado, instalação do service worker
   comprovada e manifesto que acompanha o tema.

Cada eixo traz a receita da auditoria medida, as fases com critério de
aprovação, modelos de prompt para executor e auditor, e o que fica depois da
correção: os verificadores e as especificações que impedem a dívida de voltar.

## Por onde começar

- **Projeto existente:** leia o [METODO.md](METODO.md) e comece pelo eixo com a
  maior dívida medida.
- **Projeto novo:** siga o [nascenca/BOOTSTRAP.md](nascenca/BOOTSTRAP.md) antes
  da primeira tela.
- Nos dois casos, o [METODO.md](METODO.md) é a lei; os eixos são aplicações
  dela.

## Resultados

Na primeira aplicação completa do método, numa aplicação web em produção:

- **Responsividade:** de 60 rotas com estouro de layout para zero, comprovado
  por assinatura reprodutível.
- **Tema:** de 6.606 cores fixas no código para zero, com dois temas e contraste
  validado.
- **Navegação:** de 93% quebrada para navegação que preserva o contexto.
- **PWA:** de uma instalação que não funcionava para Lighthouse 100 em produção.

No caminho, 12 pareceres de auditoria adversarial e 3 defeitos reais do produto
encontrados.

## Licença

Apache 2.0. Veja [LICENSE](LICENSE).
