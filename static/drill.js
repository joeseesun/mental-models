/* 练一练：情境判断题。条目 JSON 的 drill 字段是 3 道题，一次一道，选完给讲解。 */
(function () {
  var host = document.getElementById('drill'), dataEl = document.getElementById('mm-data');
  if (!host || !dataEl) return;
  var qs = JSON.parse(dataEl.textContent).drill;
  if (!qs || !qs.length) return;
  var i = 0, right = 0, picked = false;
  function esc(s) { return String(s).replace(/[&<>]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; }); }
  function bar() {
    return '<div class="dr-prog">' + qs.map(function (_, k) { return '<i class="' + (k < i ? 'done' : k === i ? 'cur' : '') + '"></i>'; }).join('') + '<span>第 ' + (i + 1) + ' / ' + qs.length + ' 题</span></div>';
  }
  function ask() {
    var q = qs[i]; picked = false;
    host.innerHTML = bar() + '<p class="dr-scene">' + esc(q.scene) + '</p><p class="dr-ask">' + esc(q.ask) + '</p>' +
      '<div class="dr-opts">' + q.options.map(function (o, k) { return '<button class="dr-opt" data-k="' + k + '"><b>' + 'ABCD'[k] + '</b><span>' + esc(o) + '</span></button>'; }).join('') + '</div>' +
      '<div class="dr-ex" hidden></div>';
    [].forEach.call(host.querySelectorAll('.dr-opt'), function (b) { b.onclick = function () { pick(+b.dataset.k); }; });
  }
  function pick(k) {
    if (picked) return; picked = true;
    var q = qs[i], ok = k === q.answer; if (ok) right++;
    [].forEach.call(host.querySelectorAll('.dr-opt'), function (b) {
      var n = +b.dataset.k; b.disabled = true;
      if (n === q.answer) b.classList.add('ok'); else if (n === k) b.classList.add('no'); else b.classList.add('dim');
    });
    var ex = host.querySelector('.dr-ex'); ex.hidden = false;
    ex.innerHTML = '<p class="dr-verdict ' + (ok ? 'ok' : 'no') + '">' + (ok ? '答对了' : '再想想，答案是 ' + 'ABCD'[q.answer]) + '</p><p>' + esc(q.explain) + '</p>' +
      '<button class="pl-btn go" id="dr-next">' + (i + 1 < qs.length ? '下一题 →' : '看结果 →') + '</button>';
    host.querySelector('#dr-next').onclick = function () { i++; i < qs.length ? ask() : done(); };
  }
  function done() {
    var n = qs.length, msg = right === n ? '全对。这个模型你已经能拿来用了。' : right >= n - 1 ? '差一点。回头看看错的那题的讲解，边界处最容易栽。' : '这个模型的坑不少，上面的「什么时候它会坑你」值得再读一遍。';
    host.innerHTML = '<div class="dr-result"><p class="dr-big">' + right + ' / ' + n + '</p><p>' + msg + '</p><button class="pl-btn go" id="dr-again">再练一次</button></div>';
    host.querySelector('#dr-again').onclick = function () { i = 0; right = 0; ask(); };
  }
  ask();
})();
