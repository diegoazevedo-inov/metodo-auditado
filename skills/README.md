# Skills invocáveis do kit

Quatro skills no formato `.claude/skills/<nome>/SKILL.md` — copie a pasta da skill para
o `.claude/skills/` do projeto-alvo e invoque com `/auditar-<eixo>`.

Cada skill faz o PASSO 1 do método no eixo: **auditoria medida** (números, não opinião)
e devolve o esqueleto do PLAN com ranking e recomendação de fases — apontando para o
documento do eixo em `remediacao/` como manual completo.

| Skill | Eixo | Produz |
|---|---|---|
| `auditar-tema` | Tema claro/escuro | contagem de cores hardcoded por espécie/arquivo + plano T0→T2 |
| `auditar-fluxos` | Navegação/contexto | % de voltar hardcoded, filtros fora da URL + plano F0→F2 |
| `auditar-responsividade` | Harmonia | páginas sem classe responsiva, nowrap, tabelas soltas + plano H0→H2 |
| `auditar-pwa` | PWA | runtimeCaching/manifest/SW reais vs. a política segura + plano H3 |

As skills NÃO corrigem nada — medem e planejam. A execução segue o protocolo
(executor → handoff → auditoria) com os prompts-molde de `remediacao/prompts/`.
