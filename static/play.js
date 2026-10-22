/* 可玩演示：条目页 JSON 里的 play 字段按 kind 选组件。
   gamble（测测你）/ survivors（跑一千次）/ chain（活的模拟）。颜色一律读站点 token。 */
(function () {
  var host = document.getElementById('play'), dataEl = document.getElementById('mm-data');
  if (!host || !dataEl) return;
  var spec = JSON.parse(dataEl.textContent).play;
  if (!spec) return;

  function css(el, n) { return getComputedStyle(el).getPropertyValue(n).trim(); }
  function h(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function sizeCanvas(cv, w, hgt) {
    var r = window.devicePixelRatio || 1;
    cv.width = Math.round(w * r); cv.height = Math.round(hgt * r);
    cv.style.width = w + 'px'; cv.style.height = hgt + 'px';
    var c = cv.getContext('2d'); c.setTransform(r, 0, 0, r, 0, 0); return c;
  }
  // 固定种子：滑块拖动时场景连续变化，不会每次重洗牌
  function rng(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function sliders(box, params, onChange) {
    var vals = {};
    params.forEach(function (p) {
      vals[p.id] = p.default;
      var lab = h('label', null, '<span>' + p.label + '</span><input type="range" min="' + p.min + '" max="' + p.max + '" step="' + p.step + '" value="' + p.default + '"><output></output>');
      var inp = lab.querySelector('input'), out = lab.querySelector('output');
      function show() { out.textContent = p.fmt === 'pct' ? Math.round(vals[p.id] * 100) + '%' : vals[p.id]; }
      inp.oninput = function () { vals[p.id] = +inp.value; show(); onChange(vals); };
      show(); box.appendChild(lab);
    });
    return vals;
  }
  function money(n) { return (n < 0 ? '−' : '') + Math.abs(Math.round(n)); }

  /* ---------- 测测你：真金白银的赌局，答完算出你的损失厌恶系数 ---------- */
  function gamble() {
    var q = 0, ans = [], bal = 1000, missed = 0, luck = 0, busy = false;
    var wrap = h('div', 'pl-gamble');
    host.appendChild(wrap);
    function ask() {
      var g = spec.gains[q], total = spec.gains.length, w = g / (g + spec.loss) * 100;
      wrap.innerHTML = '<p class="pl-intro">' + spec.intro + '</p>' +
        '<div class="pl-top"><div class="pl-bal"><small>你的账户</small><b>¥<span id="pl-bal">' + bal + '</span></b></div>' +
        '<div class="pl-prog">' + spec.gains.map(function (_, i) { return '<i class="' + (i < q ? 'done' : i === q ? 'cur' : '') + '"></i>'; }).join('') + '<span>第 ' + (q + 1) + ' / ' + total + ' 题</span></div></div>' +
        '<div class="pl-stage"><div class="side win" style="flex:' + w + '"><small>正面 · 50%</small><b>+' + g + '</b><em>' + spec.unit + '</em></div>' +
        '<div class="coin" id="pl-coin"><div class="face f">正</div><div class="face b">反</div></div>' +
        '<div class="side lose" style="flex:' + (100 - w) + '"><small>反面 · 50%</small><b>−' + spec.loss + '</b><em>' + spec.unit + '</em></div></div>' +
        '<div class="pl-verdict" id="pl-verdict" aria-live="polite"></div>' +
        '<div class="pl-btns" id="pl-btns"><button class="pl-btn go" data-a="1">赌一把</button><button class="pl-btn" data-a="0">不赌</button></div>';
      [].forEach.call(wrap.querySelectorAll('.pl-btn'), function (b) { b.onclick = function () { decide(b.dataset.a === '1'); }; });
    }
    function decide(bet) {
      if (busy) return; busy = true;
      var g = spec.gains[q], ev = (g - spec.loss) / 2, btns = wrap.querySelector('#pl-btns'), v = wrap.querySelector('#pl-verdict'), coin = wrap.querySelector('#pl-coin');
      ans.push(bet); btns.innerHTML = '';
      function next() {
        btns.innerHTML = '<button class="pl-btn go">' + (q + 1 < spec.gains.length ? '下一题 →' : '看结果 →') + '</button>';
        btns.firstChild.onclick = function () { busy = false; q++; q < spec.gains.length ? ask() : reveal(); };
      }
      if (!bet) {
        if (ev > 0) missed += ev;
        v.className = 'pl-verdict calm'; v.innerHTML = '你没有出手。' + (ev > 0 ? '这一局按概率算，平均每次能赚 <b>' + ev + '</b> ' + spec.unit + '，你放弃了。' : '这一局期望值刚好是 0，不赌不亏。');
        return next();
      }
      var win = Math.random() < 0.5;
      coin.className = 'coin ' + (win ? 'flip-win' : 'flip-lose');
      v.className = 'pl-verdict'; v.innerHTML = '硬币在空中……';
      setTimeout(function () {
        var d = win ? g : -spec.loss; bal += d; luck += d;
        v.className = 'pl-verdict ' + (win ? 'won' : 'lost');
        v.innerHTML = (win ? '正面！你赢了 <b>+' + g : '反面……你输了 <b>−' + spec.loss) + '</b> ' + spec.unit + '。' + (ev > 0 ? '这一局长期平均是赚 ' + ev + '，这一次只是运气。' : '');
        wrap.querySelector('#pl-bal').textContent = bal; next();
      }, 1250);
    }
    function reveal() {
      var acc = null, band, label, text;
      spec.gains.forEach(function (g, i) { if (ans[i] && acc === null) acc = g; });
      var lam = acc === null ? null : acc / spec.loss;
      if (lam === null) { label = spec.never.label; text = spec.never.text; }
      else { for (var i = 0; i < spec.bands.length; i++) if (lam <= spec.bands[i].max) { band = spec.bands[i]; break; } label = band.label; text = band.text; }
      var lo = 0.8, hi = 3.4, pos = function (v) { return Math.max(0, Math.min(100, (v - lo) / (hi - lo) * 100)); };
      var rows = spec.gains.map(function (g, i) {
        var ev = (g - spec.loss) / 2;
        return '<tr class="' + (ans[i] ? '' : 'no') + '"><td>+' + g + '</td><td>' + (ev >= 0 ? '+' : '') + ev + '</td><td>' + (ans[i] ? '赌了' : '没赌') + '</td></tr>';
      }).join('');
      var shareText = '我的损失厌恶系数' + (lam === null ? '超过 3.0' : '约为 ' + lam.toFixed(2)) + '（' + label + '）。研究里的中位数是 2.25，你呢？ ' + location.href;
      wrap.innerHTML = '<div class="pl-result"><p class="pl-big">' + (lam === null ? '> 3.0' : '≈ ' + lam.toFixed(2)) + '<small>你的损失厌恶系数 λ</small></p>' +
        '<h3>' + label + '</h3><p>' + text + '</p>' +
        '<div class="pl-score"><div><b>' + money(missed) + '</b><span>你放弃的期望收益（' + spec.unit + '）</span></div><div><b class="' + (luck >= 0 ? 'up' : 'dn') + '">' + (luck >= 0 ? '+' : '') + money(luck) + '</b><span>本次实际输赢，靠的是运气</span></div></div>' +
        '<div class="pl-gauge"><div class="bar"></div>' +
        '<span class="mk ref" style="left:' + pos(2.25) + '%"><i></i>研究中位数 2.25</span>' +
        '<span class="mk you" style="left:' + (lam === null ? 100 : pos(lam)) + '%"><i></i>你</span></div>' +
        '<table class="pl-tbl"><thead><tr><th>赢额（' + spec.unit + '）</th><th>每次期望值</th><th>你的选择</th></tr></thead><tbody>' + rows + '</tbody></table>' +
        '<p class="pl-note">' + spec.note + '</p>' +
        '<div class="pl-btns"><button class="pl-btn go" id="pl-again">再测一次</button><button class="pl-btn" id="pl-share">复制我的结果</button></div></div>';
      wrap.querySelector('#pl-again').onclick = function () { q = 0; ans = []; bal = 1000; missed = 0; luck = 0; ask(); };
      var sb = wrap.querySelector('#pl-share');
      sb.onclick = function () {
        try { navigator.clipboard.writeText(shareText).then(function () { sb.textContent = '已复制 ✓'; }, function () { sb.textContent = '复制失败，请手动选中'; }); } catch (e) { sb.textContent = '浏览器不支持复制'; }
      };
    }
    ask();
  }

  /* ---------- 跑一千次：每年淘汰一半，看最后站着的人 ---------- */
  function survivors() {
    var years = spec.years, p = spec.p, n, alive, alpha, year, anim = null;
    var wrap = h('div', 'pl-surv'), ctl = h('div', 'controls'), stat = h('div', 'pl-stat'), cv = h('canvas', 'pl-canvas'), bar = h('div', 'pl-btns'), msg = h('div', 'pl-msg');
    wrap.appendChild(h('p', 'pl-intro', spec.intro));
    wrap.appendChild(ctl); wrap.appendChild(stat); wrap.appendChild(cv); wrap.appendChild(bar); wrap.appendChild(msg);
    host.appendChild(wrap);
    var bStep = h('button', 'pl-btn go', '过一年'), bAll = h('button', 'pl-btn', '快进到底'), bReset = h('button', 'pl-btn', '重来');
    bar.appendChild(bStep); bar.appendChild(bAll); bar.appendChild(bReset);
    var hist, cols, cell, W, hgt, ctx;
    function layout() {
      W = Math.max(280, wrap.clientWidth); cols = Math.max(10, Math.floor(Math.sqrt(n * W / 260)));
      var rows = Math.ceil(n / cols); cell = W / cols; hgt = Math.ceil(rows * cell);
      ctx = sizeCanvas(cv, W, hgt);
    }
    function reset() {
      cancelAnimationFrame(anim); n = vals.n; year = 0; hist = [n];
      alive = []; alpha = []; for (var i = 0; i < n; i++) { alive.push(true); alpha.push(1); }
      msg.innerHTML = ''; bStep.disabled = bAll.disabled = false; layout(); draw(); stats();
    }
    function count() { var k = 0; for (var i = 0; i < n; i++) if (alive[i]) k++; return k; }
    function stats() {
      var k = count();
      stat.innerHTML = '<div><b>' + year + ' / ' + years + '</b>年</div><div><b>' + k + '</b>仍在连赢</div><div><b>' + (n - k) + '</b>已出局</div>' +
        '<div class="trail">' + hist.join(' → ') + '</div>';
    }
    function draw() {
      var acc = css(wrap, '--dc'), mut = css(wrap, '--line-strong'), r = Math.max(1.2, cell * 0.34);
      ctx.clearRect(0, 0, W, hgt);
      var k = count(), last = year >= years;
      for (var i = 0; i < n; i++) {
        var x = (i % cols + .5) * cell, y = (Math.floor(i / cols) + .5) * cell;
        ctx.beginPath();
        if (alive[i]) {
          if (last && k < 40) { ctx.fillStyle = acc; ctx.globalAlpha = .18; ctx.arc(x, y, r * 4.6, 0, 6.2832); ctx.fill(); ctx.beginPath(); ctx.globalAlpha = 1; ctx.arc(x, y, r * 2.1, 0, 6.2832); }
          else { ctx.globalAlpha = 1; ctx.arc(x, y, r, 0, 6.2832); }
          ctx.fillStyle = acc;
        } else { ctx.fillStyle = mut; ctx.globalAlpha = 0.25 + 0.75 * alpha[i]; ctx.arc(x, y + (1 - alpha[i]) * cell * 1.1, r * (0.55 + .45 * alpha[i]), 0, 6.2832); }
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }
    function step(done) {
      if (year >= years) return done && done();
      year++;
      var dying = [];
      for (var i = 0; i < n; i++) if (alive[i] && Math.random() >= p) { alive[i] = false; alpha[i] = 1; dying.push(i); }
      hist.push(count()); stats();
      var t0 = performance.now();
      (function f(t) {
        var k = Math.min(1, (t - t0) / 420);
        dying.forEach(function (i) { alpha[i] = 1 - k; });
        draw();
        if (k < 1) anim = requestAnimationFrame(f); else { dying.forEach(function (i) { alpha[i] = 0; }); draw(); if (year >= years) finish(); done && done(); }
      })(t0);
    }
    function finish() {
      var k = count(); bStep.disabled = bAll.disabled = true;
      if (k > 0 && spec.cover) {
        msg.innerHTML = '<div class="pl-cover"><small>' + spec.cover.kicker + '</small><b>' + spec.cover.headline.replace('{y}', years) + '</b><span>' + spec.cover.sub + '</span><em>以上为虚构的封面，用来说明幸存者会怎样被报道</em></div>' +
          '<p>' + spec.win.replace('{k}', '<b>' + k + '</b>').replace('{y}', years) + '</p>';
      } else msg.innerHTML = '<p>' + (k > 0 ? spec.win.replace('{k}', '<b>' + k + '</b>').replace('{y}', years) : spec.none) + '</p>';
    }
    bStep.onclick = function () { step(); };
    bAll.onclick = function () { bStep.disabled = bAll.disabled = true; (function loop() { if (year >= years) return; step(function () { if (year < years) setTimeout(loop, 160); }); })(); };
    bReset.onclick = reset;
    var vals = sliders(ctl, spec.params, function () { reset(); });
    addEventListener('resize', function () { layout(); draw(); });
    reset();
  }

  /* ---------- 活的模拟：二维渗流，点一下放入中子 ---------- */
  function chain() {
    var C = spec.cols, R = spec.rows, N = C * R;
    var rnd = rng(20260101), site = [], bond = [];
    for (var i = 0; i < N; i++) { site.push(rnd()); bond.push([rnd(), rnd(), rnd(), rnd()]); }
    var wrap = h('div', 'pl-chain'), ctl = h('div', 'controls'), cv = h('canvas', 'pl-canvas pl-dark'), stat = h('div', 'pl-stat'), msg = h('p', 'pl-msg');
    wrap.appendChild(h('p', 'pl-intro', spec.intro)); wrap.appendChild(ctl); wrap.appendChild(cv); wrap.appendChild(stat); wrap.appendChild(msg);
    host.appendChild(wrap);
    var W, hgt, cell, ctx, age, present, total, burned, steps, timer, origin = -1, kLast = 0, kSum = 0, kN = 0, flash = 0;
    function build() { present = []; total = 0; for (var i = 0; i < N; i++) { var p = site[i] < vals.density; present.push(p); if (p) total++; } }
    function layout() { W = Math.max(280, wrap.clientWidth); cell = W / C; hgt = Math.ceil(cell * R); ctx = sizeCanvas(cv, W, hgt); }
    function draw() {
      var acc = css(wrap, '--dc');
      ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
      ctx.fillStyle = '#0c0c0e'; ctx.fillRect(0, 0, W, hgt);
      for (var i = 0; i < N; i++) {
        if (!present[i] || age[i] >= 0) continue;
        ctx.beginPath(); ctx.fillStyle = 'rgba(190,190,200,.42)';
        ctx.arc((i % C + .5) * cell, (Math.floor(i / C) + .5) * cell, cell * .24, 0, 6.2832); ctx.fill();
      }
      ctx.globalCompositeOperation = 'lighter';
      for (var j = 0; j < N; j++) {
        var a = age[j]; if (a < 0) continue;
        var x = (j % C + .5) * cell, y = (Math.floor(j / C) + .5) * cell, fresh = steps - a;
        var glow = fresh < 3 ? 1 - fresh * .28 : 0;
        if (glow > 0) { ctx.beginPath(); ctx.fillStyle = acc; ctx.globalAlpha = .22 * glow; ctx.arc(x, y, cell * 1.5, 0, 6.2832); ctx.fill(); }
        ctx.beginPath(); ctx.fillStyle = acc; ctx.globalAlpha = fresh < 2 ? 1 : Math.max(.3, 1 - fresh * .05); ctx.arc(x, y, cell * (fresh < 2 ? .46 : .32), 0, 6.2832); ctx.fill();
      }
      ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
    }
    function report(final) {
      var pct = total ? burned / total : 0;
      stat.innerHTML = '<div><b>' + burned + '</b>已裂变</div><div><b>' + Math.round(pct * 100) + '%</b>占全部原子</div><div><b>' + steps + '</b>代</div>' +
        '<div><b class="' + (kLast > 1.05 ? 'hot' : '') + '">' + (kN ? kLast.toFixed(2) : '—') + '</b>本代倍增系数 k</div>';
      if (!final) return;
      msg.textContent = pct < .04 ? spec.fizzle : pct < .35 ? spec.partial : spec.boom;
      msg.className = 'pl-msg ' + (pct < .04 ? 'cold' : pct < .35 ? '' : 'hot');
    }
    function ignite(at) {
      clearTimeout(timer); age = []; for (var i = 0; i < N; i++) age.push(-1);
      var best = -1, bd = 1e9, ax = at % C, ay = Math.floor(at / C);
      for (var j = 0; j < N; j++) if (present[j]) { var dx = j % C - ax, dy = Math.floor(j / C) - ay, d = dx * dx + dy * dy; if (d < bd) { bd = d; best = j; } }
      if (best < 0) return;
      origin = at; age[best] = 0; burned = 1; steps = 0; kLast = 0; kSum = 0; kN = 0; var front = [best];
      msg.textContent = ''; msg.className = 'pl-msg'; draw(); report(false);
      (function tick() {
        var next = [];
        front.forEach(function (c) {
          var x = c % C, y = Math.floor(c / C), nb = [[x, y - 1], [x + 1, y], [x, y + 1], [x - 1, y]];
          nb.forEach(function (q, d) {
            if (q[0] < 0 || q[1] < 0 || q[0] >= C || q[1] >= R) return;
            var k = q[1] * C + q[0];
            if (present[k] && age[k] < 0 && bond[c][d] < vals.capture) { age[k] = steps + 1; next.push(k); burned++; }
          });
        });
        if (!next.length) { draw(); report(true); return; }
        kLast = next.length / front.length; kSum += kLast; kN++;
        steps++; front = next; draw(); report(false);
        timer = setTimeout(tick, 48);
      })();
    }
    cv.style.cursor = 'crosshair';
    cv.onclick = function (ev) {
      var r = cv.getBoundingClientRect();
      ignite(Math.min(R - 1, Math.floor((ev.clientY - r.top) / cell)) * C + Math.min(C - 1, Math.floor((ev.clientX - r.left) / cell)));
    };
    var vals = sliders(ctl, spec.params, function () { build(); ignite(origin < 0 ? mid() : origin); });
    function mid() { return Math.floor(R / 2) * C + Math.floor(C / 2); }
    addEventListener('resize', function () { layout(); draw(); });
    build(); layout(); ignite(mid());
  }

  ({ gamble: gamble, survivors: survivors, chain: chain })[spec.kind]();
})();
