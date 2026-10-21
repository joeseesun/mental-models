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
      grid: { left: 52, right: 24, top: 48, bottom: 40 },
      legend: { textStyle: { color: v('--chart-text') } },
      tooltip: { trigger: 'axis' }
    };
    return Object.assign(o, extra || {});
  }
  function themed(opt, accent) {
    var o = JSON.parse(JSON.stringify(opt));
    var axis = { axisLine: { lineStyle: { color: v('--chart-grid') } }, axisLabel: { color: v('--chart-text') },
                 nameTextStyle: { color: v('--chart-text') }, splitLine: { lineStyle: { color: v('--chart-grid') } } };
    ['xAxis', 'yAxis'].forEach(function (k) {
      if (!o[k]) return;
      o[k] = [].concat(o[k]).map(function (a) { return Object.assign({}, a, axis); });
      if (o[k].length === 1) o[k] = o[k][0];
    });
    var b = baseOption();
    b.color = [accent].concat(b.color.filter(function (c) { return c !== accent; }));
    return Object.assign(b, o, { color: b.color, textStyle: b.textStyle });
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
    return themed({
      tooltip: { formatter: function (p) { return p.data && p.data.name ? p.data.name + (p.data.ghost ? '（待写）' : '') : ''; } },
      series: [{
        type: 'graph', layout: 'force', roam: true, draggable: true,
        force: { repulsion: onlyFocus ? 220 : 160, edgeLength: onlyFocus ? 90 : 80, gravity: 0.08 },
        label: { show: true, color: v('--text'), fontSize: 12, position: 'right' },
        edgeSymbol: ['none', 'arrow'], edgeSymbolSize: 6,
        lineStyle: { color: v('--muted'), opacity: 0.55, width: 1 },
        data: nodes.map(function (n) {
          var c = dc(n.domain);
          return {
            id: n.id, name: n.name, ghost: n.ghost, symbolSize: n.focus ? 30 : (n.ghost ? 12 : 20),
            itemStyle: n.ghost
              ? { color: 'transparent', borderColor: v('--red'), borderWidth: 1.5, borderType: 'dashed' }
              : { color: c },
            label: n.ghost ? { color: v('--red') } : {}
          };
        }),
        links: links
      }]
    }, v('--d-systems'));
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
        var nodes = [{ id: d.slug, name: d.mermaid ? document.querySelector('h1').firstChild.textContent.trim() : d.slug, domain: d.domain, ghost: false, focus: true }]
          .concat(d.related.map(function (r) { return { id: r.slug, name: r.title, domain: d.domain, ghost: !r.exists }; }));
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
    document.querySelectorAll('.chip').forEach(function (b) {
      b.onclick = function () {
        document.querySelectorAll('.chip').forEach(function (x) { x.classList.toggle('on', x === b); });
        document.querySelectorAll('.card').forEach(function (cd) {
          cd.style.display = (b.dataset.f === 'all' || cd.dataset.domain === b.dataset.f) ? '' : 'none';
        });
      };
    });
  }
})();
