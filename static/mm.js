/* 运行时渲染：主题切换、Pele（Mermaid 渲染器）、ECharts（含 demo 滑块）、图谱。
   颜色全部来自 style.css 的 token（pele 走 --pele-* 映射），生成内容里不允许自带颜色。 */
(function () {
  var root = document.documentElement;
  try { var t = localStorage.getItem('mm-theme'); if (t) root.setAttribute('data-theme', t); } catch (e) {}
  function isDark() {
    var t = root.getAttribute('data-theme');
    return t ? t === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  }
  function v(n) { return getComputedStyle(root).getPropertyValue(n).trim(); }
  function dc(domain) { return v('--d-' + domain); }
  var DOMS = ['physics', 'biology', 'economics', 'psychology', 'systems', 'strategy'];

  var btn = document.querySelector('[data-theme-toggle]');
  if (btn) btn.onclick = function () {
    var n = isDark() ? 'light' : 'dark';
    root.setAttribute('data-theme', n);
    try { localStorage.setItem('mm-theme', n); } catch (e) {}
    location.reload();
  };

  // 打赏/关注弹窗：按钮打开，✕、Esc、点击遮罩关闭
  document.querySelectorAll('[data-modal-open]').forEach(function (b) {
    b.onclick = function () {
      var m = document.getElementById(b.getAttribute('data-modal-open'));
      if (m) { m.hidden = false; var c = m.querySelector('[data-close]'); if (c) c.focus(); }
    };
  });
  document.querySelectorAll('.modal').forEach(function (m) {
    var close = function () { m.hidden = true; };
    m.addEventListener('click', function (ev) { if (ev.target === m) close(); });
    var c = m.querySelector('[data-close]');
    if (c) c.onclick = close;
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') document.querySelectorAll('.modal:not([hidden])').forEach(function (m) { m.hidden = true; });
  });

  function baseOption(extra) {
    var o = {
      color: DOMS.map(dc),
      textStyle: { color: v('--chart-text'), fontFamily: 'inherit' },
      grid: { left: 12, right: 28, top: 40, bottom: 28, containLabel: true },
      legend: { show: false },
      tooltip: { trigger: 'axis', backgroundColor: v('--paper'), borderColor: v('--line-strong'), borderWidth: 1,
                 textStyle: { color: v('--text'), fontSize: 13 }, extraCssText: 'border-radius:10px;box-shadow:0 8px 24px -8px rgba(0,0,0,.2)' }
    };
    return Object.assign(o, extra || {});
  }
  function themed(opt, accent) {
    var o = JSON.parse(JSON.stringify(opt));
    var axis = { axisLine: { lineStyle: { color: v('--line-strong') } }, axisTick: { show: false },
                 axisLabel: { color: v('--chart-text'), fontSize: 12 },
                 nameTextStyle: { color: v('--muted'), fontSize: 12 },
                 splitLine: { lineStyle: { color: v('--chart-grid'), type: 'dashed' } } };
    ['xAxis', 'yAxis'].forEach(function (k) {
      if (!o[k]) return;
      o[k] = [].concat(o[k]).map(function (a) {
        var m = Object.assign({}, a, axis);
        if (a.type === 'category') m.splitLine = { show: false };
        if (k === 'xAxis' && a.name) { m.nameLocation = 'middle'; m.nameGap = 32; }
        if (k === 'yAxis' && a.type !== 'category') m.axisLine = { show: false };
        return m;
      });
      if (o[k].length === 1) o[k] = o[k][0];
    });
    var n = (o.series || []).length, horiz = o.yAxis && !Array.isArray(o.yAxis) && o.yAxis.type === 'category';
    (o.series || []).forEach(function (sr, i) {
      if (sr.type === 'bar') {
        sr.barMaxWidth = 30;
        sr.itemStyle = Object.assign({ borderRadius: horiz ? [0, 5, 5, 0] : [5, 5, 0, 0] }, sr.itemStyle);
        if (n === 1 && sr.data && sr.data.length <= 9 && !sr.label) sr.label = { show: true, position: horiz ? 'right' : 'top', color: v('--text'), fontSize: 12, fontFamily: v('--mono') };
      } else if (sr.type === 'line') {
        sr.lineStyle = Object.assign({ width: 2.6 }, sr.lineStyle);
        if (sr.showSymbol === undefined) { sr.symbol = 'circle'; sr.symbolSize = 7; }
        if (n === 1 && !sr.areaStyle) sr.areaStyle = { opacity: 0.12 };
      }
    });
    var b = baseOption();
    b.color = [accent, v('--text'), v('--muted')].concat(b.color.filter(function (c) { return c !== accent; }));
    if (n > 1) { b.legend = { show: true, top: 0, left: 0, icon: 'roundRect', itemWidth: 14, itemHeight: 4, textStyle: { color: v('--chart-text'), fontSize: 12.5 } }; b.grid.top = 44; }
    var out = Object.assign(b, o, { color: b.color, textStyle: b.textStyle });
    if (o.legend && n > 1) out.legend = Object.assign({}, b.legend, o.legend);
    else if (n <= 1) out.legend = { show: false };
    return out;
  }

  function renderMermaid(src) {
    var el = document.getElementById('mermaid');
    if (!el || !window.pele) return;
    pele.mount(el, src, { zoom: false, onError: function () { el.setAttribute('data-render-error', '1'); } });
  }

  function evalSeries(d, vals) {
    var xs = [], x = d.x;
    for (var i = x.from; i <= x.to + 1e-9; i += x.step) xs.push(+i.toFixed(6));
    var names = ['x'].concat(d.params.map(function (p) { return p.id; }));
    var ms = ['sin','cos','exp','log','pow','min','max','sqrt','abs','log2','log10','floor','ceil','round'];
    var fns = d.series.map(function (s) {
      var body = 'var {' + ms.join(',') + '}=Math,PI=Math.PI,E=Math.E;return (' + s.expr + ');';
      return new Function(names.join(','), body);
    });
    return {
      xs: xs,
      ys: fns.map(function (f) {
        return xs.map(function (xv) {
          var args = [xv].concat(d.params.map(function (p) { return vals[p.id]; }));
          var y = f.apply(null, args);
          return isFinite(y) ? +y.toFixed(4) : null;
        });
      })
    };
  }

  function renderDemo(d, accent) {
    var host = document.getElementById('demo'), ctl = document.getElementById('demo-controls');
    if (!host || !window.echarts) return;
    var chart = echarts.init(host), vals = {};
    d.params.forEach(function (p) { vals[p.id] = p.default; });
    function draw() {
      var r = evalSeries(d, vals);
      chart.setOption(themed({
        xAxis: { type: 'category', name: d.x.label, data: r.xs },
        yAxis: { type: 'value' },
        series: d.series.map(function (s, i) { return { name: s.name, type: 'line', smooth: true, showSymbol: false, data: r.ys[i] }; }),
        legend: { data: d.series.map(function (s) { return s.name; }) }
      }, accent), true);
    }
    d.params.forEach(function (p) {
      var lab = document.createElement('label');
      lab.innerHTML = '<span>' + p.label + '</span><input type="range" min="' + p.min + '" max="' + p.max + '" step="' + p.step + '" value="' + p.default + '"><output>' + p.default + '</output>';
      var inp = lab.querySelector('input'), out = lab.querySelector('output');
      inp.oninput = function () { vals[p.id] = +inp.value; out.textContent = inp.value; draw(); };
      ctl.appendChild(lab);
    });
    draw();
    addEventListener('resize', function () { chart.resize(); });
  }

  function graphOption(nodes, links, onlyFocus) {
    var deg = {};
    links.forEach(function (l) { deg[l.source] = (deg[l.source] || 0) + 1; deg[l.target] = (deg[l.target] || 0) + 1; });
    return {
      textStyle: { fontFamily: 'inherit' },
      tooltip: { formatter: function (p) { return p.data && p.data.name ? p.data.name + (p.data.ghost ? '（待写）' : '') : ''; },
                 backgroundColor: v('--paper'), borderColor: v('--line-strong'), textStyle: { color: v('--text'), fontSize: 13 } },
      series: [{
        type: 'graph', layout: 'force', roam: true, draggable: true, cursor: 'pointer', center: null, zoom: onlyFocus ? 1 : 1.05,
        force: { initLayout: 'circular', repulsion: onlyFocus ? 260 : 300, edgeLength: onlyFocus ? [70, 120] : [60, 150], gravity: onlyFocus ? 0.08 : 0.06, friction: 0.12 },
        label: { show: true, color: v('--text'), fontSize: onlyFocus ? 13 : 11, position: 'right', distance: 5 },
        labelLayout: { hideOverlap: true },
        scaleLimit: { min: 0.6, max: 4 },
        emphasis: { focus: 'adjacency', scale: 1.2, label: { show: true, fontWeight: 700 }, lineStyle: { width: 2, opacity: 0.9 } },
        lineStyle: { color: v('--muted'), opacity: 0.28, width: 1, curveness: 0.08 },
        data: nodes.map(function (n) {
          var c = dc(n.domain), size = n.focus ? 34 : onlyFocus ? 18 : 9 + Math.min(deg[n.id] || 0, 12) * 1.3;
          return {
            id: n.id, name: n.name, ghost: n.ghost, symbolSize: size, cursor: n.ghost || n.focus ? 'default' : 'pointer',
            itemStyle: n.ghost
              ? { color: 'transparent', borderColor: v('--red'), borderWidth: 1.5, borderType: 'dashed' }
              : { color: c, borderColor: v('--paper'), borderWidth: 2 },
            label: n.ghost ? { color: v('--red') } : (n.focus ? { fontWeight: 700, fontSize: 15 } : (!onlyFocus && (deg[n.id] || 0) < 7 ? { show: false } : {}))
          };
        }),
        links: links
      }]
    };
  }

  function wireGraphClicks(chart, slugs, prefix) {
    chart.on('click', function (p) {
      if (p.dataType === 'node' && !p.data.ghost && slugs[p.data.id]) location.href = prefix + 'm/' + p.data.id + '/';
    });
  }

  // 条目页
  var dataEl = document.getElementById('mm-data');
  if (dataEl) {
    var d = JSON.parse(dataEl.textContent), accent = dc(d.domain);
    window.addEventListener('load', function () {
      renderMermaid(d.mermaid);
      var ev = document.getElementById('chart');
      if (ev && window.echarts) { var c = echarts.init(ev); c.setOption(themed(d.echarts, accent)); addEventListener('resize', function () { c.resize(); }); }
      renderDemo(d.demo, accent);
      var mg = document.getElementById('mini-graph');
      if (mg && window.echarts) {
        var nodes = [{ id: d.slug, name: d.title, domain: d.domain, ghost: false, focus: true }]
          .concat(d.related.map(function (r) { return { id: r.slug, name: r.title, domain: r.domain || d.domain, ghost: !r.exists }; }));
        var links = d.related.map(function (r) { return { source: d.slug, target: r.slug }; });
        var g = echarts.init(mg); g.setOption(graphOption(nodes, links, true));
        var s = {}; nodes.forEach(function (n) { s[n.id] = 1; }); wireGraphClicks(g, s, '../../');
        addEventListener('resize', function () { g.resize(); });
      }
    });
  }

  // 首页
  var hg = document.getElementById('home-graph');
  if (hg) {
    fetch('graph.json').then(function (r) { return r.json(); }).then(function (g) {
      var c = echarts.init(hg); c.setOption(graphOption(g.nodes, g.links, false));
      var s = {}; g.nodes.forEach(function (n) { if (!n.ghost) s[n.id] = 1; }); wireGraphClicks(c, s, '');
      addEventListener('resize', function () { c.resize(); });
    });
    var cards = [].slice.call(document.querySelectorAll('.card')), secs = [].slice.call(document.querySelectorAll('[data-domain-sec]'));
    var q = document.getElementById('q'), empty = document.getElementById('empty');
    q.oninput = function () {
      var k = q.value.trim().toLowerCase(), shown = 0;
      cards.forEach(function (c) { var m = !k || c.dataset.q.indexOf(k) > -1; c.hidden = !m; if (m) shown++; });
      secs.forEach(function (sc) { sc.hidden = !!k && !sc.querySelector('.card:not([hidden])'); });
      empty.hidden = shown > 0;
    };
    // 今日模型：按日期稳定轮换
    var td = document.getElementById('today');
    if (td && cards.length) {
      var day = Math.floor(Date.now() / 864e5), c = cards[day % cards.length];
      td.className = 'today tint dom-' + c.dataset.domain; td.href = 'm/' + c.dataset.slug + '/';
      td.querySelector('.glyph').outerHTML = c.querySelector('.glyph').outerHTML;
      td.querySelector('h2').textContent = c.dataset.title; td.querySelector('.en').textContent = c.dataset.en;
      td.querySelector('p').textContent = c.dataset.tag;
    }
    // 领域导航高亮
    var chips = [].slice.call(document.querySelectorAll('.chip'));
    function mark(f) { chips.forEach(function (x) { x.classList.toggle('on', x.dataset.f === f); }); }
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (en) { if (en.isIntersecting) mark(en.target.dataset.domainSec); });
      }, { rootMargin: '-30% 0px -60% 0px' });
      secs.forEach(function (sc) { io.observe(sc); });
      var top = new IntersectionObserver(function (es) { if (es[0].isIntersecting) mark('all'); }, { rootMargin: '0px 0px -85% 0px' });
      top.observe(document.querySelector('.map-sec'));
    }
  }

  // 条目页目录滚动高亮
  var toc = document.querySelector('.toc');
  if (toc && 'IntersectionObserver' in window) {
    var links = {};
    [].forEach.call(toc.querySelectorAll('a'), function (a) { links[a.getAttribute('href').slice(1)] = a; });
    var spy = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        if (!en.isIntersecting) return;
        Object.keys(links).forEach(function (k) { links[k].classList.toggle('on', k === en.target.id); });
      });
    }, { rootMargin: '-20% 0px -70% 0px' });
    [].forEach.call(document.querySelectorAll('.sec'), function (sc) { spy.observe(sc); });
  }
})();
