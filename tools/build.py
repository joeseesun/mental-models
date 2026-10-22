#!/usr/bin/env python3
"""静态构建：data/models/*.json → dist/。只用标准库；Pele（Mermaid 渲染器）/ ECharts 走 CDN，在浏览器里渲染。

产出：首页（力导向图谱 + 条目卡片 + 待写清单）、/m/<slug>/ 条目页、graph.json、search.json、待写清单。
引用不存在的条目 → 红链（虚线节点），同时进入 dist/todo.json。
"""
import html
import json
import shutil
import sys
from collections import defaultdict

from mm import DIST, DOMAINS, ROOT, load_all, validate

STATIC = ROOT / 'static'
LEVEL_LABEL = {'verified': '一手核实', 'secondary': '可靠二手', 'draft': '草稿示意'}
SITE = 'https://mm.qiaomu.ai'
UMAMI_ID = '07f649b7-1176-4d0b-9a02-63d40e21d193'
CDN = ('<script src="https://cdn.jsdelivr.net/npm/pele@1.8.0/dist/pele.global.js"></script>'
       '<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>')

e = html.escape

MODALS = """<div class="modal" id="reward-modal" hidden><div class="modal-box" role="dialog" aria-modal="true" aria-labelledby="reward-title">
<button class="modal-close" data-close aria-label="关闭">✕</button>
<h3 id="reward-title">打赏支持</h3>
<img class="qr" src="{up}qiaomu_reward_qr.png" alt="打赏二维码" width="220" height="220">
</div></div>
<div class="modal" id="follow-modal" hidden><div class="modal-box" role="dialog" aria-modal="true" aria-labelledby="follow-title">
<button class="modal-close" data-close aria-label="关闭">✕</button>
<h3 id="follow-title">关注向阳乔木</h3>
<img class="qr" src="{up}qiaomu_wechat_public_account_qr.jpg" alt="公众号二维码" width="220" height="220">
<p class="modal-note">公众号：向阳乔木推荐看</p>
<p class="modal-links"><a href="https://github.com/joeseesun/mental-models" target="_blank" rel="noopener">GitHub</a> · <a href="https://x.com/vista8" target="_blank" rel="noopener">X</a></p>
</div></div>"""


def page(title, body, desc='', depth=0, extra='', path=''):
    up = '../' * depth
    url = f'{SITE}/{path}' if path else SITE + '/'
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
<link rel="stylesheet" href="{up}style.css">{CDN}
<script defer src="https://umami.qiaomu.ai/script.js" data-website-id="{UMAMI_ID}" data-domains="mm.qiaomu.ai"></script></head>
<body data-root="{up}">
<header class="site-header"><div class="wrap header-inner">
<a class="brand" href="{up}index.html">思维模型 Wiki<i>Mental Models</i></a>
<nav><a href="{up}index.html#d-physics">物理</a><a href="{up}index.html#d-psychology">心理</a><a href="{up}index.html#d-strategy">战略</a></nav>
<button class="chrome-btn" type="button" data-modal-open="reward-modal" aria-label="打赏支持" title="打赏支持">♡</button>
<button class="chrome-btn" type="button" data-modal-open="follow-modal" aria-label="关注向阳乔木" title="关注向阳乔木">✚</button>
<button class="theme-toggle" type="button" data-theme-toggle aria-label="切换明暗主题">◐</button>
</div></header>
{body}
<footer class="site-footer"><div class="wrap">
<div>数据是唯一的真实来源：网页、图谱与视频都从 data/models/*.json 派生。出处分三级：一手核实、可靠二手、草稿示意。</div>
<div class="footer-links"><a href="https://github.com/joeseesun/mental-models" target="_blank" rel="noopener">GitHub</a><a href="https://x.com/vista8" target="_blank" rel="noopener">X</a><a href="https://tuijian.qiaomu.ai/" target="_blank" rel="noopener">乔木推荐</a></div>
</div></footer>
{MODALS.format(up=up)}
<script src="{up}mm.js"></script>{extra}
</body></html>"""


GLYPHS = {
    'physics': '<ellipse cx="50" cy="50" rx="44" ry="16"/><ellipse cx="50" cy="50" rx="44" ry="16" transform="rotate(60 50 50)"/><ellipse cx="50" cy="50" rx="44" ry="16" transform="rotate(120 50 50)"/><circle class="f" cx="50" cy="50" r="5"/><circle class="f" cx="92" cy="44" r="3"/><circle class="f" cx="22" cy="26" r="3"/>',
    'biology': '<circle cx="50" cy="50" r="42"/><circle cx="36" cy="42" r="15"/><circle cx="62" cy="62" r="9"/><circle class="f" cx="36" cy="42" r="4"/><circle class="f" cx="64" cy="34" r="3"/><path d="M14 68 C30 78 44 80 58 78"/>',
    'economics': '<path d="M12 10 V88 H92"/><path d="M18 78 C42 72 62 34 90 16"/><path d="M18 20 C42 32 62 70 90 82"/><circle class="f" cx="54" cy="49" r="4.5"/><path d="M54 49 V88 M54 49 H12" stroke-dasharray="2 4"/>',
    'psychology': '<circle cx="38" cy="40" r="27"/><circle cx="62" cy="40" r="27"/><circle cx="50" cy="63" r="27"/><circle class="f" cx="50" cy="48" r="3.5"/>',
    'systems': '<path d="M50 18 L18 70 L82 70 Z M50 18 L50 50 M18 70 L50 50 M82 70 L50 50 M50 18 L90 32 M82 70 L90 32 M18 70 L10 34 M50 18 L10 34"/><circle class="f" cx="50" cy="18" r="5"/><circle class="f" cx="18" cy="70" r="5"/><circle class="f" cx="82" cy="70" r="5"/><circle class="f" cx="50" cy="50" r="4"/><circle class="f" cx="90" cy="32" r="3.5"/><circle class="f" cx="10" cy="34" r="3.5"/>',
    'strategy': '<rect x="10" y="10" width="80" height="80" rx="3"/><path d="M30 10 V90 M50 10 V90 M70 10 V90 M10 30 H90 M10 50 H90 M10 70 H90"/><path d="M20 80 L40 60 H60 L80 20" stroke-width="2.4"/><circle class="f" cx="80" cy="20" r="5"/><circle class="f" cx="20" cy="80" r="3.5"/>',
}
DOMAIN_INTRO = {
    'physics': '力、能量、熵：世界运转的底层规律',
    'biology': '演化、生态、免疫：生命系统的生存策略',
    'economics': '激励、稀缺、博弈：资源如何流动',
    'psychology': '偏误、动机、说服：人怎么看、想、选',
    'systems': '反馈、涌现、瓶颈：整体大于部分之和',
    'strategy': '取舍、护城河、先手：在不确定里下注',
}
ORDERS = {  # 按领域气质决定区块先后：心理先讲反例，物理系统先动手，经济战略先看数据
    'psychology': ['hook', 'limits', 'principle', 'evidence', 'demo', 'howto', 'related', 'sources'],
    'physics': ['hook', 'demo', 'principle', 'evidence', 'howto', 'limits', 'related', 'sources'],
    'systems': ['hook', 'demo', 'principle', 'evidence', 'howto', 'limits', 'related', 'sources'],
    'economics': ['hook', 'evidence', 'principle', 'howto', 'demo', 'limits', 'related', 'sources'],
    'strategy': ['hook', 'evidence', 'howto', 'principle', 'demo', 'limits', 'related', 'sources'],
    'biology': ['hook', 'principle', 'evidence', 'demo', 'howto', 'limits', 'related', 'sources'],
}
PLAY_LABEL = {'gamble': '测测你', 'survivors': '跑一千次', 'chain': '活的模拟'}
LABELS = {'hook': '场景钩子', 'principle': '原理图', 'evidence': '数据证据', 'demo': '交互演示',
          'howto': '怎么用', 'limits': '失效边界', 'related': '关联模型', 'sources': '出处'}


def glyph(domain):
    return f'<span class="glyph" aria-hidden="true"><svg viewBox="0 0 100 100">{GLYPHS[domain]}</svg></span>'


def badge(level):
    return f'<span class="lv lv-{level}">{LEVEL_LABEL[level]}</span>'


def roster_order(models):
    try:
        r = json.loads((ROOT / 'data' / 'roster.json').read_text('utf-8'))['models']
        order = [m['slug'] for m in r if m['slug'] in models]
    except Exception:
        order = []
    return order + [s for s in models if s not in order]


def model_page(d, all_models, order):
    s, dom = d['slug'], d['domain']
    idx = order.index(s)
    no = f'№ {idx + 1:03d}'
    experts = ''.join(f'<div class="expert"><b>{e(x["name"])}</b>{e(x["role"])}</div>' for x in d['experts'])
    ev, demo = d['evidence'], d['demo']
    series_types = {x.get('type') for x in ev['echarts'].get('series', [])}
    single_bar = len(ev['echarts'].get('series', [])) == 1 and series_types == {'bar'}
    play = d.get('play')
    n_rel = sum(1 for r in d['related'] if r['slug'] in all_models)

    def sec(key, i, inner, cls=''):
        return (f'<section class="sec {cls}" id="s-{key}"><p class="sec-label">{i:02d} · {LABELS[key]}</p>{inner}</section>')

    def b_hook():
        short = len(d['hook']['story']) < 232
        cls = 'hook-quote' if short else 'hook-prose'
        return f'<h2>{e(d["hook"]["title"])}</h2><div class="{cls}"><p>{e(d["hook"]["story"])}</p></div>'

    def b_principle():
        return f'<div id="mermaid" class="figure"></div><p class="caption">{e(d["principle"]["caption"])}</p>'

    def b_evidence():
        h = f'<h2>{e(ev["title"])} {badge(ev["level"])}</h2>'
        src = f'<p class="src">来源：{e(ev["source"])}</p>'
        if single_bar:
            return (h + '<div class="ev-split"><div><p class="takeaway">' + e(ev['takeaway']) + '</p>' + src +
                    '</div><div id="chart" class="figure chart"></div></div>')
        return h + f'<p class="takeaway-wide">{e(ev["takeaway"])}</p><div id="chart" class="figure chart"></div><p class="caption">来源：{e(ev["source"])}</p>'

    def b_demo():
        if play:
            return (f'<h2>{e(play["title"])}</h2><div class="demo-box play-box"><div id="play" class="play"></div>'
                    f'<p class="takeaway">{e(play["takeaway"])}</p></div>')
        return (f'<h2>{e(demo["title"])}</h2><div class="demo-box"><div id="demo-controls" class="controls"></div>'
                f'<div id="demo" class="figure chart"></div><p class="takeaway">{e(demo["takeaway"])}</p></div>')

    def b_howto():
        items = ''.join(f'<li><b>{e(h["step"])}</b><span>{e(h["detail"])}</span></li>' for h in d['howto'])
        return f'<ol class="steps{" grid2" if len(d["howto"]) <= 4 else ""}">{items}</ol>'

    def b_limits():
        if len(d['limits']) <= 4:
            cards = ''.join(
                f'<div class="limit"><p class="sit">{e(r["situation"])}</p>'
                f'<p class="says"><small>模型会说</small>{e(r["model_says"])}</p>'
                f'<p class="real"><small>现实是</small>{e(r["reality"])}</p></div>' for r in d['limits'])
            return f'<h2>什么时候它会坑你</h2><div class="limit-cards">{cards}</div>'
        rows = ''.join(f'<tr><td>{e(r["situation"])}</td><td>{e(r["model_says"])}</td><td>{e(r["reality"])}</td></tr>' for r in d['limits'])
        return ('<h2>什么时候它会坑你</h2><div class="table-wrap"><table class="limits"><thead><tr><th>情境</th><th>模型的说法</th><th>现实</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div>')

    def b_related():
        cards = ''
        for r in d['related']:
            if r['slug'] in all_models:
                t = all_models[r['slug']]
                cards += (f'<a class="rel-card dom-{t["domain"]}" style="--rc:var(--dc)" href="../{r["slug"]}/"><b><span class="dot"></span>{e(t["title"])}</b>'
                          f'<span>{e(r["relation"])}</span></a>')
            else:
                cards += f'<div class="rel-card"><b><span class="redlink" title="待写">{e(r["slug"])}</span></b><span>{e(r["relation"])}</span></div>'
        prev_s = order[idx - 1] if idx > 0 else None
        next_s = order[idx + 1] if idx + 1 < len(order) else None
        pager = '<div class="pager">' + (
            f'<a href="../{prev_s}/"><small>← 上一个</small><b>{e(all_models[prev_s]["title"])}</b></a>' if prev_s else '<span></span>') + (
            f'<a href="../{next_s}/"><small>下一个 →</small><b>{e(all_models[next_s]["title"])}</b></a>' if next_s else '<span></span>') + '</div>'
        return f'<div id="mini-graph" class="figure mini"></div><div class="rel-grid">{cards}</div><div style="height:28px"></div>{pager}'

    def b_sources():
        return '<ul>' + ''.join(f'<li>{e(x["title"])} {badge(x["level"])}</li>' for x in d['sources']) + '</ul>'

    builders = {'hook': b_hook, 'principle': b_principle, 'evidence': b_evidence, 'demo': b_demo,
                'howto': b_howto, 'limits': b_limits, 'related': b_related, 'sources': b_sources}
    keys = list(ORDERS[dom])
    if play:  # 可玩演示紧跟钩子，别埋在后面
        keys.remove('demo')
        keys.insert(1, 'demo')
    body_secs = ''.join(sec(k, i + 1, builders[k](), 'sources' if k == 'sources' else '') for i, k in enumerate(keys))
    toc = ''.join(f'<a href="#s-{k}"><i>{i + 1:02d}</i>{LABELS[k]}</a>' for i, k in enumerate(keys))
    payload = json.dumps({
        'slug': s, 'title': d['title'], 'domain': dom, 'mermaid': d['principle']['mermaid'],
        'echarts': ev['echarts'], 'demo': demo, 'play': play,
        'related': [{'slug': r['slug'], 'title': all_models.get(r['slug'], {}).get('title', r['slug']),
                     'domain': all_models.get(r['slug'], {}).get('domain', dom),
                     'exists': r['slug'] in all_models} for r in d['related']],
    }, ensure_ascii=False).replace('</', '<\\/')
    body = f"""<div class="dom-{dom}">
<header class="cover tint">{glyph(dom)}
<div class="wrap"><div class="cover-inner">
<p class="crumb"><a href="../../index.html">首页</a><span>/</span><a href="../../index.html#d-{dom}">{e(DOMAINS[dom])}</a><span>/</span><span class="no">{no}</span></p>
<h1>{e(d['title'])}</h1><p class="en">{e(d['en'])}</p>
<p class="tagline">{e(d['tagline'])}</p>
<div class="experts">{experts}</div>
<div class="facts"><div>证据等级<b>{LEVEL_LABEL[ev['level']]}</b></div><div>{'互动形式' if play else '可调参数'}<b>{PLAY_LABEL[play['kind']] if play else str(len(demo['params'])) + ' 个'}</b></div><div>关联模型<b>{n_rel} 个</b></div><div>参考出处<b>{len(d['sources'])} 条</b></div></div>
</div></div></header>
<div class="wrap layout"><aside class="toc"><p class="h">本页内容</p>{toc}</aside>
<main class="article">{body_secs}</main></div></div>
<script type="application/json" id="mm-data">{payload}</script>"""
    return page(f'{d["title"]} · 思维模型 Wiki', body, d['tagline'], depth=2, path=f'm/{s}/',
                extra=f'<script src="../../play.js"></script>' if play else '')


def index_page(models, ghosts, order):
    def card(s):
        d = models[s]
        return (f'<a class="card dom-{d["domain"]}" data-domain="{d["domain"]}" data-q="{e(d["title"] + d["en"] + d["tagline"] + "".join(x["name"] for x in d["experts"])).lower()}" '
                f'data-slug="{s}" data-title="{e(d["title"])}" data-en="{e(d["en"])}" data-tag="{e(d["tagline"])}" href="m/{s}/">'
                f'{glyph(d["domain"])}<span class="no"><span>№ {order.index(s) + 1:03d}</span></span>'
                f'<h3>{e(d["title"])}</h3><div class="en">{e(d["en"])}</div><p>{e(d["tagline"])}</p>'
                f'<span class="who">{e("、".join(x["name"] for x in d["experts"]))}</span></a>')
    secs = ''
    for k, v in DOMAINS.items():
        ms = [s for s in order if models[s]['domain'] == k]
        secs += (f'<section class="domain-sec dom-{k}" id="d-{k}" data-domain-sec="{k}"><div class="domain-head">{glyph(k)}'
                 f'<div><h2>{v}</h2><p>{DOMAIN_INTRO[k]}</p></div><span class="n">{len(ms)} 个模型</span></div>'
                 f'<div class="grid">{"".join(card(s) for s in ms)}</div></section>')
    chips = '<a class="chip on" href="#all" data-f="all">全部</a>' + ''.join(
        f'<a class="chip dom-{k}" href="#d-{k}" data-f="{k}"><span class="dot"></span>{v}</a>' for k, v in DOMAINS.items())
    legend = ''.join(f'<a class="dom-{k}" href="#d-{k}"><span class="dot"></span>{v}</a>' for k, v in DOMAINS.items())
    first = models[order[0]]
    todo = ''.join(
        f'<li><span class="redlink">{e(g)}</span> 被 {"、".join(e(models[r]["title"]) for r in refs)} 引用</li>'
        for g, refs in ghosts.items())
    todo_sec = f'<section class="domain-sec" id="todo"><div class="sec-head"><h2>待写清单</h2></div><ul class="todo">{todo}</ul></section>' if todo else ''
    n_links = sum(len(d['related']) for d in models.values())
    body = f"""<main class="wrap" id="all">
<section class="hero"><div>
<p class="eyebrow">Mental Models · 向阳乔木</p>
<h1>专家思维的<em>可视化</em>解剖台</h1>
<p class="lede">每个模型讲清四件事：从哪来、怎么运转、什么时候用、什么时候失效。配原理图、真实数据和能拖动的演示。</p>
<div class="search"><input id="q" type="search" placeholder="搜模型、英文名或人名，例如 芒格" autocomplete="off" aria-label="搜索"></div>
<div class="stats"><div><b>{len(models)}</b>思维模型</div><div><b>{len(DOMAINS)}</b>学科领域</div><div><b>{n_links}</b>模型关联</div></div>
</div>
<a class="today tint dom-{first['domain']}" id="today" href="m/{order[0]}/">{glyph(first['domain'])}
<span class="tag">今日模型</span><h2>{e(first['title'])}</h2><div class="en">{e(first['en'])}</div><p>{e(first['tagline'])}</p><span class="go">开始阅读 →</span></a>
</section>
<section class="map-sec"><div class="sec-head"><h2>知识图谱</h2><span>点击节点跳转 · 滚轮缩放 · 可拖动</span></div>
<div id="home-graph" class="home-graph"></div><div class="legend">{legend}</div></section>
<nav class="domain-nav" id="domain-nav">{chips}</nav>
{secs}<p class="empty" id="empty" hidden>没有找到匹配的模型</p>
{todo_sec}
</main>"""
    return page('思维模型 Wiki', body, '用图讲清全球专家的思维框架')


def main():
    models = load_all()
    bad = {s: validate(d, models) for s, d in models.items()}
    bad = {s: p for s, p in bad.items() if p}
    if bad:
        for s, p in bad.items():
            print(f'[校验失败] {s}', *p, sep='\n  - ')
        sys.exit(1)

    order = roster_order(models)
    ghosts = defaultdict(list)
    edges = []
    for s, d in models.items():
        for r in d['related']:
            edges.append({'source': s, 'target': r['slug']})
            if r['slug'] not in models:
                ghosts[r['slug']].append(s)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for f in STATIC.iterdir():
        shutil.copy(f, DIST / f.name)

    for s, d in models.items():
        out = DIST / 'm' / s
        out.mkdir(parents=True)
        (out / 'index.html').write_text(model_page(d, models, order), 'utf-8')

    graph = {
        'nodes': [{'id': s, 'name': d['title'], 'domain': d['domain'], 'ghost': False} for s, d in models.items()]
                 + [{'id': g, 'name': g, 'domain': 'systems', 'ghost': True} for g in ghosts],
        'links': edges,
    }
    (DIST / 'graph.json').write_text(json.dumps(graph, ensure_ascii=False), 'utf-8')
    (DIST / 'todo.json').write_text(json.dumps(ghosts, ensure_ascii=False, indent=1), 'utf-8')
    (DIST / 'search.json').write_text(json.dumps(
        [{'slug': s, 'title': d['title'], 'en': d['en'], 'tagline': d['tagline'],
          'experts': [x['name'] for x in d['experts']]} for s, d in models.items()], ensure_ascii=False), 'utf-8')
    today = __import__('datetime').date.today().isoformat()
    (DIST / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'<url><loc>{SITE}/</loc><lastmod>{today}</lastmod><priority>1.0</priority></url>\n'
        + ''.join(f'<url><loc>{SITE}/m/{s}/</loc><lastmod>{today}</lastmod></url>\n' for s in models)
        + '</urlset>\n', 'utf-8')
    (DIST / 'robots.txt').write_text(
        'User-agent: *\nAllow: /\n'
        f'Sitemap: {SITE}/sitemap.xml\n', 'utf-8')
    (DIST / 'index.html').write_text(index_page(models, ghosts, order), 'utf-8')
    print(f'构建完成：{len(models)} 个条目，{len(ghosts)} 个待写 -> {DIST}')


if __name__ == '__main__':
    main()
