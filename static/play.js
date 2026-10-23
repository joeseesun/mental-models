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


  /* ---------- 对战演示：和四个隐藏性格的对手各打十局囚徒困境 ---------- */
  function dilemma() {
    var M = spec.matrix, R = spec.rounds, wrap = h('div', 'pl-dil'), done = {};
    host.appendChild(wrap);
    var ops = spec.opponents.slice().sort(function () { return Math.random() - .5; });
    ops.forEach(function (o, i) { o.tag = 'ABCD'.charAt(i); });
    function pay(a, b) { return a && b ? M.R : a ? M.S : b ? M.T : M.P; }
    function policy(id, hist) {
      if (id === 'alld') return 0;
      if (id === 'allc') return 1;
      if (id === 'tft') return hist.length ? hist[hist.length - 1].me : 1;
      return hist.some(function (x) { return !x.me; }) ? 0 : 1;
    }
    function simulate(id, mover) {
      var hist = [], s = 0;
      for (var i = 0; i < R; i++) { var op = policy(id, hist), me = mover(i, hist); s += pay(me, op); hist.push({ me: me, op: op }); }
      return s;
    }
    var matrix = '<table class="pl-mx"><tr><th></th><th>对手合作</th><th>对手背叛</th></tr>' +
      '<tr><th>你合作</th><td><b>' + M.R + '</b> / ' + M.R + '</td><td><b>' + M.S + '</b> / ' + M.T + '</td></tr>' +
      '<tr><th>你背叛</th><td><b>' + M.T + '</b> / ' + M.S + '</td><td><b>' + M.P + '</b> / ' + M.P + '</td></tr></table>' +
      '<p class="pl-note">格子里左边是你的得分，右边是对手的得分。</p>';
    function pick() {
      wrap.innerHTML = '<p class="pl-intro">' + spec.intro + '</p>' + matrix +
        '<div class="pl-opps">' + ops.map(function (o) {
          var d = done[o.id];
          return '<button class="opp' + (d ? ' played' : '') + '" data-id="' + o.id + '"><i>' + o.tag + '</i><b>对手 ' + o.tag + '</b><span>' + (d ? '已打过，你得 ' + d.score + ' 分' : '性格隐藏，十局后揭晓') + '</span></button>';
        }).join('') + '</div>';
      [].forEach.call(wrap.querySelectorAll('.opp'), function (b) { b.onclick = function () { play(ops.filter(function (o) { return o.id === b.dataset.id; })[0]); }; });
    }
    function play(o) {
      var hist = [], me = 0, them = 0;
      function view(msg) {
        wrap.innerHTML = '<div class="pl-top"><div class="pl-bal"><small>对手 ' + o.tag + '</small><b>' + me + ' : ' + them + '</b></div>' +
          '<div class="pl-prog">' + Array.apply(null, Array(R)).map(function (_, i) { return '<i class="' + (i < hist.length ? 'done' : i === hist.length ? 'cur' : '') + '"></i>'; }).join('') + '<span>第 ' + Math.min(hist.length + 1, R) + ' / ' + R + ' 局</span></div></div>' +
          '<div class="pl-hist"><div><small>你</small>' + hist.map(function (x) { return '<i class="' + (x.me ? 'c' : 'd') + '">' + (x.me ? '合' : '背') + '</i>'; }).join('') + '</div>' +
          '<div><small>对手</small>' + hist.map(function (x) { return '<i class="' + (x.op ? 'c' : 'd') + '">' + (x.op ? '合' : '背') + '</i>'; }).join('') + '</div></div>' +
          '<div class="pl-verdict">' + (msg || '这一局你选什么？') + '</div>' +
          '<div class="pl-btns"><button class="pl-btn go" data-m="1">合作</button><button class="pl-btn" data-m="0">背叛</button></div>';
        [].forEach.call(wrap.querySelectorAll('.pl-btn'), function (b) { b.onclick = function () { move(+b.dataset.m); }; });
      }
      function move(m) {
        var op = policy(o.id, hist), a = pay(m, op), b = pay(op, m);
        hist.push({ me: m, op: op }); me += a; them += b;
        if (hist.length >= R) return reveal();
        view('上一局：你' + (m ? '合作' : '背叛') + '，对手' + (op ? '合作' : '背叛') + '，你得 ' + a + ' 分。');
      }
      function reveal() {
        done[o.id] = { score: me };
        var seq = hist.map(function (x) { return x.me; });
        var allc = simulate(o.id, function () { return 1; }), alld = simulate(o.id, function () { return 0; }), tft = simulate(o.id, function (i, hs) { return hs.length ? hs[hs.length - 1].op : 1; });
        var rest = Object.keys(done).length < ops.length;
        wrap.innerHTML = '<div class="pl-result"><p class="pl-big">' + me + '<small>你的得分，满分 ' + (M.T * R) + '</small></p>' +
          '<h3>对手 ' + o.tag + ' 是「' + o.name + '」</h3><p>' + o.desc + '</p><p>' + ((spec.insights && spec.insights[o.id]) || '') + '</p>' +
          '<table class="pl-tbl"><thead><tr><th>如果你从头到尾用……</th><th>会得到</th></tr></thead><tbody>' +
          '<tr><td>永远合作</td><td>' + allc + '</td></tr><tr><td>永远背叛</td><td>' + alld + '</td></tr><tr><td>一报还一报</td><td>' + tft + '</td></tr><tr class="you"><td>你实际打的</td><td>' + me + '</td></tr></tbody></table>' +
          '<div class="pl-btns"><button class="pl-btn go" id="pl-next">' + (rest ? '再换一个对手' : '重新开始') + '</button></div></div>';
        wrap.querySelector('#pl-next').onclick = function () { if (!rest) done = {}; pick(); };
      }
      view();
    }
    pick();
  }

  /* ---------- 牧场模拟：五个牧民共用一块会再生的草地 ---------- */
  function commons() {
    var N = spec.herders, T = spec.seasons, K = spec.capacity, G = spec.regrow, EAT = spec.eat, P = spec.price;
    var wrap = h('div', 'pl-com'), S, t, ai, grass, rows, mine, group, cows;
    host.appendChild(wrap);
    function round(x) { return Math.round(x); }
    function graze(stock, d) {
      var e = d > 0 ? Math.min(stock, EAT * d) : 0, per = d > 0 ? P * e / d : 0, left = stock - e;
      return { per: per, left: left + G * left * (1 - left / K) };
    }
    function bench() {
      var s = K, tot = 0, target = Math.round(N * 1.6);
      for (var i = 0; i < T; i++) { var r = graze(s, target); tot += r.per * target; s = r.left; }
      return round(tot);
    }
    function reset() { S = K; t = 0; ai = []; for (var i = 0; i < N - 1; i++) ai.push(2); grass = [K]; rows = []; mine = 0; group = 0; cows = 2; view(); }
    function chart() {
      var w = 520, hh = 110, pts = grass.map(function (g, i) { return (i / T * w).toFixed(1) + ',' + (hh - g / K * (hh - 8) - 4).toFixed(1); }).join(' ');
      return '<svg class="pl-spark" viewBox="0 0 ' + w + ' ' + hh + '" preserveAspectRatio="none"><line x1="0" x2="' + w + '" y1="' + (hh - 4) + '" y2="' + (hh - 4) + '"/><polyline points="' + pts + '"/></svg>';
    }
    function view() {
      var pct = Math.round(S / K * 100), low = S < 25;
      wrap.innerHTML = '<p class="pl-intro">' + spec.intro + '</p>' +
        '<div class="pl-top"><div class="pl-bal"><small>你的累计收入</small><b>' + round(mine) + '</b></div><div class="pl-prog">' +
        Array.apply(null, Array(T)).map(function (_, i) { return '<i class="' + (i < t ? 'done' : i === t ? 'cur' : '') + '"></i>'; }).join('') + '<span>第 ' + Math.min(t + 1, T) + ' / ' + T + ' 季</span></div></div>' +
        '<div class="pl-grass' + (low ? ' low' : '') + '"><small>草场 ' + pct + '%</small><div><i style="width:' + pct + '%"></i></div></div>' + chart() +
        '<div class="pl-step"><span>这一季你放几头牛</span><button data-d="-1" aria-label="少放一头">−</button><b id="pl-cows">' + cows + '</b><button data-d="1" aria-label="多放一头">+</button></div>' +
        '<div class="pl-btns"><button class="pl-btn go" id="pl-go">放牧</button></div>' +
        (rows.length ? '<table class="pl-tbl"><thead><tr><th>季度</th><th>你放</th><th>其他人共放</th><th>草场剩</th><th>你每头牛赚</th></tr></thead><tbody>' + rows.slice(-5).reverse().join('') + '</tbody></table>' : '');
      [].forEach.call(wrap.querySelectorAll('.pl-step button'), function (b) { b.onclick = function () { cows = Math.max(0, Math.min(8, cows + +b.dataset.d)); wrap.querySelector('#pl-cows').textContent = cows; }; });
      wrap.querySelector('#pl-go').onclick = season;
    }
    function season() {
      var others = ai.reduce(function (a, b) { return a + b; }, 0), d = cows + others, r = graze(S, d);
      mine += r.per * cows; group += r.per * d; S = r.left; t++; grass.push(S);
      rows.push('<tr><td>' + t + '</td><td>' + cows + '</td><td>' + others + '</td><td>' + round(S / K * 100) + '%</td><td>' + r.per.toFixed(1) + '</td></tr>');
      ai = ai.map(function (a) {
        var oth = (cows + others - a) / (N - 1), tgt = Math.round(.5 * a + .5 * oth + [-1, 0, 0, 1][Math.floor(Math.random() * 4)]);
        if (S < 35) tgt -= 1;
        return Math.max(1, Math.min(6, tgt));
      });
      if (t >= T) return end();
      view();
    }
    function end() {
      var b = bench(), gone = S < 8;
      wrap.innerHTML = '<div class="pl-result"><p class="pl-big">' + round(mine) + '<small>你的累计收入</small></p>' +
        '<h3>' + (gone ? '草场被啃光了' : S < 40 ? '草场只剩下一小半' : '草场撑住了') + '</h3>' +
        '<p>' + (gone ? '最后草长不出来，每头牛都吃不饱。' : S < 40 ? '再来几季，草场就撑不住了。' : '大家放得克制，草场能长回来。') + '</p>' +
        '<div class="pl-score"><div><b>' + round(group) + '</b><span>五个牧民合计的收入</span></div><div><b class="up">' + b + '</b><span>如果统一管理，每季只放 ' + Math.round(N * 1.6) + ' 头牛，合计的收入</span></div></div>' +
        chart() + '<p class="pl-note">其他四个牧民会看着大家的牛数调整自己的数，草场低了会收一点。</p>' +
        '<div class="pl-btns"><button class="pl-btn go" id="pl-again">再来一局</button></div></div>';
      wrap.querySelector('#pl-again').onclick = reset;
    }
    reset();
  }

  /* ---------- 拍卖演示：共同价值的密封拍卖，体验赢家诅咒 ---------- */
  function auction() {
    var R = spec.rounds, n = spec.bidders, LO = spec.low, HI = spec.high, NZ = spec.noise, SH = spec.botShade || 16;
    var wrap = h('div', 'pl-auc'), q, hist, v, est, bots, bid;
    host.appendChild(wrap);
    function rnd(a, b) { return a + Math.random() * (b - a); }
    function deal() { v = rnd(LO, HI); est = []; for (var i = 0; i < n; i++) est.push(v + rnd(-NZ, NZ)); bots = est.slice(1).map(function (e) { return e - rnd(0, SH); }); }
    function reset() { q = 0; hist = []; deal(); ask(); }
    function total() { return hist.reduce(function (a, x) { return a + x.profit; }, 0); }
    function ask() {
      bid = Math.round(est[0] - 5);
      wrap.innerHTML = '<p class="pl-intro">' + spec.intro + '</p>' +
        '<div class="pl-top"><div class="pl-bal"><small>累计盈亏</small><b class="' + (total() >= 0 ? 'up' : 'dn') + '">' + (total() >= 0 ? '+' : '−') + Math.abs(Math.round(total())) + '</b></div><div class="pl-prog">' +
        Array.apply(null, Array(R)).map(function (_, i) { return '<i class="' + (i < q ? 'done' : i === q ? 'cur' : '') + '"></i>'; }).join('') + '<span>第 ' + (q + 1) + ' / ' + R + ' 轮</span></div></div>' +
        '<div class="pl-est"><small>你对这块地的估价</small><b>' + Math.round(est[0]) + '</b><span>误差范围约正负 ' + NZ + '，别人拿到的是他们自己的估价</span></div>' +
        '<div class="pl-bid"><label><span>你的出价</span><input type="range" id="pl-bid" min="' + Math.round(est[0] - 60) + '" max="' + Math.round(est[0] + 10) + '" step="1" value="' + bid + '"><output id="pl-bo">' + bid + '</output></label></div>' +
        '<div class="pl-btns"><button class="pl-btn go" id="pl-go">递交出价</button></div>';
      var inp = wrap.querySelector('#pl-bid'), out = wrap.querySelector('#pl-bo');
      inp.oninput = function () { bid = +inp.value; out.textContent = bid; };
      wrap.querySelector('#pl-go').onclick = settle;
    }
    function settle() {
      var top = Math.max.apply(null, bots), win = bid > top, profit = win ? v - bid : 0;
      hist.push({ est: est[0], bid: bid, win: win, profit: profit, v: v, top: top });
      wrap.innerHTML = '<div class="pl-verdict ' + (win ? (profit >= 0 ? 'won' : 'lost') : 'calm') + '"><b>' + (win ? (profit >= 0 ? '你赢了，赚了 ' + Math.round(profit) : '你赢了，却亏了 ' + Math.round(-profit)) : '你没赢') + '</b><br>' +
        '这块地真实值 <b>' + Math.round(v) + '</b>，你出价 ' + bid + '，别人最高出价 ' + Math.round(top) + '。' + (win && profit < 0 ? '赢下来的人，往往正是估得最高的人。' : '') + '</div>' +
        '<div class="pl-btns"><button class="pl-btn go" id="pl-next">' + (q + 1 < R ? '下一轮 →' : '看结果 →') + '</button></div>';
      wrap.querySelector('#pl-next').onclick = function () { q++; if (q < R) { deal(); ask(); } else end(); };
    }
    function expect(shade) {
      var s = 0, N = 2500;
      for (var k = 0; k < N; k++) {
        var vv = rnd(LO, HI), e0 = vv + rnd(-NZ, NZ), top = -1e9;
        for (var j = 1; j < n; j++) top = Math.max(top, vv + rnd(-NZ, NZ) - rnd(0, SH));
        if (e0 - shade > top) s += vv - (e0 - shade);
      }
      return s / N;
    }
    function end() {
      var wins = hist.filter(function (x) { return x.win; }), tot = total(), avgShade = hist.reduce(function (a, x) { return a + (x.est - x.bid); }, 0) / hist.length;
      var rows = [0, 10, 20, 30].map(function (s) { var e = expect(s); return '<tr><td>估价减 ' + s + '</td><td class="' + (e >= 0 ? 'up' : 'dn') + '">' + (e >= 0 ? '+' : '−') + Math.abs(e).toFixed(1) + '</td></tr>'; }).join('');
      wrap.innerHTML = '<div class="pl-result"><p class="pl-big ' + (tot >= 0 ? '' : 'neg') + '">' + (tot >= 0 ? '+' : '−') + Math.abs(Math.round(tot)) + '<small>' + R + ' 轮的累计盈亏</small></p>' +
        '<h3>你赢了 ' + wins.length + ' 轮，平均把估价压低了 ' + Math.round(avgShade) + '</h3>' +
        '<p>' + (!wins.length ? '你一轮都没赢：出价压得太低，什么也没拿到。要赢，就得出得更高一点，但赢下来的那一轮，常常已经亏了。' : tot >= 0 ? '你赚到了，但要小心：这几轮运气也有份。' : '你被赢家诅咒咬了：赢下来的轮次里，你多半付多了。') + '</p>' +
        '<table class="pl-tbl"><thead><tr><th>如果每次都这样出价</th><th>每轮平均盈亏（模拟数千次）</th></tr></thead><tbody>' + rows + '</tbody></table>' +
        '<p class="pl-note">每轮对手按自己的估价压低 0 到 ' + SH + ' 出价。人越多，赢的人高估得越多，需要压低的幅度也越大。</p>' +
        '<div class="pl-btns"><button class="pl-btn go" id="pl-again">再玩一遍</button></div></div>';
      wrap.querySelector('#pl-again').onclick = reset;
    }
    reset();
  }

  ({ gamble: gamble, survivors: survivors, chain: chain, dilemma: dilemma, commons: commons, auction: auction })[spec.kind]();

})();
