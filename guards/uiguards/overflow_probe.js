/*
 * GUARD 4 -- sonda de estouro por elemento, injetada na pagina.
 *
 * Cada achado e um ELEMENTO, com seletor proprio; nenhum numero da pagina
 * inteira faz esse papel. Devolve estrutura pura (sem data nem hora) para o
 * driver em Python consolidar.
 *
 * DECISAO CENTRAL DO GUARD -- a especie de cada achado sai do `overflow-x`
 * computado DO PROPRIO ELEMENTO; os ancestrais nao entram na decisao.
 * Motivo: pelas regras do CSS, se um eixo declara rolagem, o outro nao pode
 * continuar `visible` -- vira `auto`. Um painel que so declarou rolagem
 * vertical passa, portanto, a "rolar" na horizontal tambem. Se a especie
 * dependesse de algum ancestral rolar, qualquer excesso num painel assim
 * seria dado por resolvido, e defeitos reais nao chegariam ao
 * relatorio. O teste 04 da prova (sweep/prova_sonda.py) planta esse caso.
 */
(config) => {
  const PISO = config.piso;
  const LIMITE = config.limite;

  // Ordem fixa de relato: as tres do placar primeiro, a decorativa por ultimo.
  const ESPECIES = [
    "transbordo-visivel",      // o excedente fica a mostra, fora da caixa
    "recorte-sem-rolagem",     // o corte esconde conteudo e nao ha rolagem ate ele
    "rolagem-nao-declarada",   // ha rolagem horizontal que ninguem pediu
    "recorte-decorativo",      // o que o corte esconde e so enfeite
  ];
  // O PLACAR, nos termos da spec (GUARD 4, regras de decisao; historico em
  // DECISOES.md 2.1): "O placar é formado por três espécies: a do conteúdo
  // que passa visivelmente da caixa, a do conteúdo escondido sem rolagem e a
  // da rolagem horizontal não declarada. A espécie decorativa é excluída
  // dessa contagem e listada separadamente, de modo que elementos sem dano
  // visível não aumentem o placar." A ordem de relato acima nao decide nada;
  // quem decide e o filtro abaixo.
  const NO_PLACAR = new Set(ESPECIES.filter((e) => e !== "recorte-decorativo"));

  // As tres isencoes seguem a MESMA regra: so vale classe SEM variante. Uma
  // classe com prefixo de largura (md:overflow-x-auto, md:truncate) nao tem
  // efeito nas telas mais estreitas que o prefixo, e sao elas que estouram.
  // Aceitar `md:overflow-x-auto` isentava um contentor que so tinha
  // overflow-x computado como `auto` por efeito colateral da rolagem
  // VERTICAL -- 1634px de conteudo sumiam do relatorio por uma classe que
  // nao se aplicava.
  const ROLAGEM_DECLARADA = /^overflow(-x)?-(auto|scroll)$/;                  // SEM variante
  const TRUNCAMENTO_DECLARADO = /^(truncate|text-ellipsis|line-clamp-\d+)$/; // SEM variante
  const OCULTO_ACESSIVEL = /^(sr-only|visually-hidden)$/;

  const classes = (el) =>
    (typeof el.className === "string" ? el.className : el.getAttribute("class") || "")
      .split(/\s+/).filter(Boolean);

  // O marcador de prioridade (`!`, prefixo numa versao do framework e sufixo
  // na seguinte) NAO e variante: `!overflow-x-auto` se aplica em toda largura
  // e declara a mesma intencao que `overflow-x-auto`. So o `:` condiciona.
  const semPrioridade = (c) => c.replace(/^!+/, "").replace(/!+$/, "");
  const semVariante = (c) => !c.includes(":");

  function seletorLegivel(el) {
    if (!el || el.nodeType !== 1) return "";
    if (el.id) return "#" + el.id;
    const partes = [];
    let no = el, niveis = 0;
    while (no && no.nodeType === 1 && niveis < 3) {
      let p = no.tagName.toLowerCase();
      if (no.id) { partes.unshift("#" + no.id); break; }
      const cls = classes(no)
        .filter((c) => !/[[\]()/%]/.test(c) && c.length <= 24)
        .slice(0, 2);
      if (cls.length) p += "." + cls.join(".");
      const irmaos = no.parentElement
        ? [...no.parentElement.children].filter((s) => s.tagName === no.tagName) : [];
      if (irmaos.length > 1) p += `:nth-of-type(${irmaos.indexOf(no) + 1})`;
      partes.unshift(p);
      no = no.parentElement;
      niveis++;
    }
    return partes.join(" > ");
  }

  // O que o corte esconde e CONTEUDO quando o filho que transborda: e (ou
  // contem, renderizado) um elemento interativo; OU tem texto visivel; OU e
  // (ou contem, renderizado) imagem ou grafico que nao esteja marcado com
  // aria-hidden="true". Fora isso, e decoracao.
  //   - Texto visivel e perceptivel por si. Posicao absoluta, pointer-events
  //     ou aria-hidden nao o desfazem: quem enxerga le o texto cortado.
  //   - Imagem e grafico sao conteudo, salvo quando o autor os tirou da
  //     arvore de acessibilidade com aria-hidden -- a marca usual de ornamento.
  //   - Video, iframe, object e embed seguem sempre como conteudo: sao
  //     documento ou midia embutidos, nao ornamento.
  const INTERATIVO =
    'a[href], area[href], button, input:not([type="hidden"]), select, textarea, ' +
    '[role="button"], [role="link"], [role="checkbox"], [role="radio"], ' +
    '[role="switch"], [role="textbox"], [role="combobox"], [role="slider"], ' +
    '[role="spinbutton"], video, iframe, object, embed';
  const IMAGEM_OU_GRAFICO = "img, picture, svg, canvas";
  const renderizado = (e) => e.getClientRects().length > 0;
  const semAriaHidden = (e) => !e.closest('[aria-hidden="true"]');

  // O que o estilo poe na tela por ::before ou ::after, lido do `content`
  // como o navegador o serializa, da esquerda para a direita:
  //   - trecho entre aspas e texto; attr() ja chega resolvido nele;
  //   - fora das aspas, url(), image-set(), image(), cross-fade() e element(),
  //     com ou sem prefixo de fornecedor (-webkit-, -moz-), sao imagem; qualquer outra funcao (counter(), counters(), gradiente) e
  //     palavra-chave (open-quote, close-quote) nao chega como texto e nao e lida;
  //   - o que vem depois de uma barra fora das aspas e texto alternativo, que
  //     nao aparece na tela.
  // Nos trechos, os escapes do CSS sao decodificados; espaco, quebra de linha,
  // caractere de largura zero, hifen invisivel e marcas de direcao nao contam.
  // Devolve "texto" se algo legivel aparece; "grafico" se so aparece imagem ou
  // glifo de fonte de icone (caractere de uso privado), que seguem a regra das
  // imagens; null se nada aparece.
  const INVISIVEL = /[\s­​-‏‪-‮⁠-⁤⁦-⁩﻿]/gu;
  const SO_USO_PRIVADO = /^[-\u{F0000}-\u{FFFFD}\u{100000}-\u{10FFFD}]+$/u;
  const FUNCAO_DE_IMAGEM = /^(-webkit-|-moz-)?(url|image-set|image|cross-fade|element)$/i;
  const decodificarEscape = (_, hex) => {
    const cp = parseInt(hex, 16);
    return cp > 0 && cp <= 0x10FFFF ? String.fromCodePoint(cp) : "�";
  };
  function fimDasAspas(v, i) {           // v[i] abre aspas; devolve o indice que fecha
    const q = v[i];
    for (let j = i + 1; j < v.length; j++) {
      if (v[j] === "\\") { j++; continue; }
      if (v[j] === q) return j;
    }
    return v.length;
  }
  function lerContent(v) {
    const trechos = [];
    let imagem = false;
    let i = 0;
    while (i < v.length) {
      const c = v[i];
      if (c === '"' || c === "'") {
        const j = fimDasAspas(v, i);
        trechos.push(v.slice(i + 1, j));
        i = j + 1;
      } else if (c === "/") {
        break;                            // o resto e texto alternativo
      } else if (/[A-Za-z-]/.test(c)) {
        let j = i;
        while (j < v.length && /[A-Za-z0-9-]/.test(v[j])) j++;
        const nome = v.slice(i, j);
        if (v[j] === "(") {               // funcao: vai ate o ')' que a fecha
          let prof = 0, k = j;
          for (; k < v.length; k++) {
            if (v[k] === '"' || v[k] === "'") { k = fimDasAspas(v, k); continue; }
            if (v[k] === "(") prof++;
            else if (v[k] === ")" && --prof === 0) break;
          }
          if (FUNCAO_DE_IMAGEM.test(nome)) imagem = true;
          i = k + 1;
        } else {
          i = j;                          // palavra-chave: nao e texto
        }
      } else {
        i++;
      }
    }
    return { trechos, imagem };
  }
  function textoGeradoPorEstilo(e) {
    let achou = null;
    for (const pseudo of ["::before", "::after"]) {
      const cs = getComputedStyle(e, pseudo);
      if (cs.display === "none" || cs.visibility !== "visible") continue;
      const { trechos, imagem } = lerContent(cs.content || "");
      if (imagem) achou = "grafico";
      for (const bruto of trechos) {
        // Escapes decodificados numa passada so, da esquerda para a direita:
        // uma contrabarra escapada vira contrabarra literal e nao abre outro
        // escape -- o texto \20 que aparece na tela continua sendo \20.
        const trecho = bruto
          .replace(/\\(?:([0-9a-fA-F]{1,6})\s?|([\s\S]))/g,
                   (_, hex, ch) => (hex ? decodificarEscape(_, hex) : ch))
          .replace(INVISIVEL, "");
        if (!trecho) continue;
        if (!SO_USO_PRIVADO.test(trecho)) return "texto";
        achou = "grafico";
      }
    }
    return achou;
  }

  function temTextoVisivel(el) {
    const it = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n = it.nextNode(); n; n = it.nextNode()) {
      if (!n.nodeValue.trim()) continue;
      const pai = n.parentElement;
      if (!pai || !renderizado(pai)) continue;
      if (getComputedStyle(pai).visibility !== "visible") continue;
      return true;
    }
    return [el, ...el.querySelectorAll("*")].some(
      (e) => renderizado(e) && textoGeradoPorEstilo(e) === "texto");
  }

  function ehDecoracao(el) {
    if (el.matches(INTERATIVO) ||
        [...el.querySelectorAll(INTERATIVO)].some(renderizado)) return false;
    if (temTextoVisivel(el)) return false;
    const imagens = [el, ...el.querySelectorAll(IMAGEM_OU_GRAFICO)]
      .filter((e) => e.matches(IMAGEM_OU_GRAFICO) && renderizado(e));
    if (imagens.some(semAriaHidden)) return false;
    const graficosDoEstilo = [el, ...el.querySelectorAll("*")]
      .filter((e) => renderizado(e) && textoGeradoPorEstilo(e) === "grafico");
    if (graficosDoEstilo.some(semAriaHidden)) return false;
    return true;
  }

  function filhosTransbordantes(el) {
    const cx = el.getBoundingClientRect();
    const borda = parseFloat(getComputedStyle(el).borderLeftWidth) || 0;
    const limite = cx.left + borda + el.clientWidth;
    const out = [];
    for (const f of el.children) {
      if (f.getClientRects().length === 0) continue;
      const r = f.getBoundingClientRect();
      const excesso = r.right - limite;
      if (excesso > 0.5) out.push({ el: f, excesso });
    }
    out.sort((a, b) => b.excesso - a.excesso);
    return out;
  }

  // Marcacao do layout raiz, independente de estilo, que o GUARD 6 usa para
  // separar moldura de pagina. A sonda so REGISTRA, em cada achado, se ele
  // esta sob cada marcador; quem classifica e o consolidador. Como nada na
  // coleta depende da marcacao, o GUARD 6 pode pular a verificacao dela no
  // placar zero sem que isso esconda defeito algum.
  const ANC = (config.ancoras || {});

  const achados = [];
  let abaixoDoPiso = 0;
  let ignoradosIsencao = 0;

  for (const el of document.querySelectorAll("*")) {
    // Descendente de grafico vetorial fica de fora: nao e caixa de layout do
    // CSS, e larguras de conteudo/visivel nao descrevem estouro nele. O
    // <svg> em si (sem ownerSVGElement) segue medido como caixa comum.
    if (el.ownerSVGElement) continue;
    if (el.getClientRects().length === 0) continue;            // sem renderizacao

    const rect = el.getBoundingClientRect();
    const visivel = el.clientWidth;
    if (visivel <= 1 || rect.height <= 1) continue;            // caixa de tamanho desprezivel

    const conteudo = el.scrollWidth;
    const excedente = conteudo - visivel;
    if (excedente <= 0) continue;

    const cls = classes(el);

    // Texto tirado da tela e mantido para leitor de tela (sr-only e afins) nao
    // entra: o recurso consiste num corte proposital, e o guard o deixa
    // passar. Exige
    // classe SEM variante, como as outras duas isencoes: testar a classe com as
    // variantes removidas fazia `md:sr-only` isentar tambem nas larguras em
    // que ela nao se aplica.
    if (cls.some((c) => semVariante(c) && OCULTO_ACESSIVEL.test(semPrioridade(c)))) {
      ignoradosIsencao++; continue;
    }

    if (excedente < PISO) { abaixoDoPiso++; continue; }

    const cs = getComputedStyle(el);
    const ox = cs.overflowX;

    // a classe pede rolagem horizontal: o excesso e esperado e nao se acusa
    if ((ox === "auto" || ox === "scroll") &&
        cls.some((c) => semVariante(c) && ROLAGEM_DECLARADA.test(semPrioridade(c)))) {
      ignoradosIsencao++; continue;
    }
    // a classe pede truncamento: o corte e proposital, pelo mesmo raciocinio
    // da rolagem. Com prefixo de largura (md:truncate) a isencao nao vale: nas telas
    // mais estreitas que o prefixo a classe nao existe, e e nelas que o texto
    // estoura.
    if ((ox === "hidden" || ox === "clip") &&
        cls.some((c) => semVariante(c) && TRUNCAMENTO_DECLARADO.test(semPrioridade(c)))) {
      ignoradosIsencao++; continue;
    }

    let especie;
    if (ox === "auto" || ox === "scroll") {
      especie = "rolagem-nao-declarada";
    } else if (ox === "hidden" || ox === "clip") {
      const transbordantes = filhosTransbordantes(el);
      // Sem filho transbordante identificado, nao da para afirmar que so enfeite
      // foi cortado: o achado vai para o placar.
      especie = (transbordantes.length > 0 && transbordantes.every((f) => ehDecoracao(f.el)))
        ? "recorte-decorativo" : "recorte-sem-rolagem";
    } else {
      especie = "transbordo-visivel";
    }

    const maiorFilho = filhosTransbordantes(el)[0];
    achados.push({
      el,
      seletor: seletorLegivel(el),
      largura_conteudo: conteudo,
      largura_visivel: visivel,
      excedente: excedente,
      especie,
      filho_responsavel: maiorFilho ? seletorLegivel(maiorFilho.el) : null,
      no_placar: NO_PLACAR.has(especie),
      sob_ancora_moldura: !!(ANC.moldura && el.closest(ANC.moldura)),
      sob_ancora_conteudo: !!(ANC.conteudo && el.closest(ANC.conteudo)),
    });
  }

  // Quem tem outro achado dentro de si: o relatorio usa isto para apontar
  // onde mexer quando varios elementos aninhados acusam o mesmo excesso.
  for (const a of achados) {
    a.tem_achado_mais_interno = achados.some((b) => b !== a && a.el.contains(b.el));
  }

  // Ordem sempre a mesma, com desempate definido:
  // especie (ordem fixa) -> excedente decrescente -> seletor alfabetico.
  achados.sort((a, b) =>
    ESPECIES.indexOf(a.especie) - ESPECIES.indexOf(b.especie) ||
    b.excedente - a.excedente ||
    (a.seletor < b.seletor ? -1 : a.seletor > b.seletor ? 1 : 0));

  const especies = {};
  const truncado = {};
  for (const nome of ESPECIES) {
    const grupo = achados.filter((a) => a.especie === nome);
    truncado[nome] = grupo.length > LIMITE;
    especies[nome] = grupo.slice(0, LIMITE).map((a) => ({
      seletor: a.seletor,
      largura_conteudo: a.largura_conteudo,
      largura_visivel: a.largura_visivel,
      excedente: Math.round(a.excedente * 100) / 100,
      especie: a.especie,
      filho_responsavel: a.filho_responsavel,
      tem_achado_mais_interno: a.tem_achado_mais_interno,
      no_placar: a.no_placar,
      sob_ancora_moldura: a.sob_ancora_moldura,
      sob_ancora_conteudo: a.sob_ancora_conteudo,
    }));
  }

  return {
    metricas: {
      viewport_largura: window.innerWidth,
      viewport_altura: window.innerHeight,
      documento_conteudo: document.documentElement.scrollWidth,
      documento_visivel: document.documentElement.clientWidth,
      excedente_da_pagina:
        document.documentElement.scrollWidth - document.documentElement.clientWidth,
      elementos_examinados: document.querySelectorAll("*").length,
    },
    especies,
    truncado_por_especie: truncado,
    placar: achados.filter((a) => a.no_placar).length,
    decorativos: achados.filter((a) => a.especie === "recorte-decorativo").length,
    fora_do_placar: achados.filter((a) => !a.no_placar).length,
    abaixo_do_piso: abaixoDoPiso,
    ignorados_por_isencao: ignoradosIsencao,
    piso_aplicado: PISO,
    ancoras_aplicadas: { moldura: ANC.moldura || null, conteudo: ANC.conteudo || null },
    ancoras_presentes: {
      moldura: !!(ANC.moldura && document.querySelector(ANC.moldura)),
      conteudo: !!(ANC.conteudo && document.querySelector(ANC.conteudo)),
    },
  };
}
