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
<a class="brand" href="{up}index.html">思维模型 Wiki</a>
<nav><a href="{up}index.html#all">全部模型</a><a href="{up}index.html#todo">待写清单</a></nav>
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


def badge(level):
    return f'<span class="lv lv-{level}">{LEVEL_LABEL[level]}</span>'


def model_page(d, all_models):
    s = d['slug']
    experts = ' · '.join(f'<strong>{e(x["name"])}</strong>（{e(x["role"])}）' for x in d['experts'])
    howto = ''.join(f'<li><b>{e(h["step"])}</b><span>{e(h["detail"])}</span></li>' for h in d['howto'])
    limits = ''.join(
        f'<tr><td>{e(r["situation"])}</td><td>{e(r["model_says"])}</td><td>{e(r["reality"])}</td></tr>'
        for r in d['limits'])
    rel = ''.join(
        (f'<li><a href="../{r["slug"]}/">{e(all_models[r["slug"]]["title"])}</a><span>{e(r["relation"])}</span></li>'
         if r['slug'] in all_models else
         f'<li><span class="redlink" title="待写">{e(r["slug"])}</span><span>{e(r["relation"])}</span></li>')
        for r in d['related'])
    src = ''.join(f'<li>{e(x["title"])} {badge(x["level"])}</li>' for x in d['sources'])
    payload = json.dumps({
        'slug': s, 'domain': d['domain'], 'mermaid': d['principle']['mermaid'],
        'echarts': d['evidence']['echarts'], 'demo': d['demo'],
        'related': [{'slug': r['slug'], 'title': all_models.get(r['slug'], {}).get('title', r['slug']),
                     'exists': r['slug'] in all_models} for r in d['related']],
    }, ensure_ascii=False).replace('</', '<\\/')
    body = f"""<main class="wrap article dom-{d['domain']}">
<p class="crumb"><a href="../../index.html">首页</a> / {e(DOMAINS[d['domain']])}</p>
<h1>{e(d['title'])} <small>{e(d['en'])}</small></h1>
<p class="tagline"><strong>{e(d['tagline'])}</strong></p>
<p class="experts">{experts}</p>

<section><h2>场景钩子 · {e(d['hook']['title'])}</h2><p>{e(d['hook']['story'])}</p></section>
<section><h2>原理图</h2><div id="mermaid" class="figure"></div><p class="caption">{e(d['principle']['caption'])}</p></section>
<section><h2>数据证据 · {e(d['evidence']['title'])} {badge(d['evidence']['level'])}</h2>
<div id="chart" class="figure chart"></div>
<p class="caption">{e(d['evidence']['takeaway'])}<br><span class="src">来源：{e(d['evidence']['source'])}</span></p></section>
<section><h2>交互演示 · {e(d['demo']['title'])}</h2><div id="demo-controls" class="controls"></div>
<div id="demo" class="figure chart"></div><p class="caption">{e(d['demo']['takeaway'])}</p></section>
<section><h2>怎么用</h2><ol class="howto">{howto}</ol></section>
<section><h2>失效边界</h2><div class="table-wrap"><table class="limits"><thead><tr><th>情境</th><th>模型的说法</th><th>现实</th></tr></thead><tbody>{limits}</tbody></table></div></section>
<section><h2>关联模型</h2><div id="mini-graph" class="figure mini"></div><ul class="rel">{rel}</ul></section>
<section class="sources"><h2>出处</h2><ul>{src}</ul></section>
</main>
<script type="application/json" id="mm-data">{payload}</script>"""
    return page(f'{d["title"]} · 思维模型 Wiki', body, d['tagline'], depth=2, path=f'm/{s}/')


def index_page(models, ghosts):
    cards = ''.join(
        f'<a class="card dom-{d["domain"]}" data-domain="{d["domain"]}" href="m/{s}/">'
        f'<span class="dot"></span><span class="dom">{e(DOMAINS[d["domain"]])}</span>'
        f'<h3>{e(d["title"])}</h3><p>{e(d["tagline"])}</p>'
        f'<span class="who">{e("、".join(x["name"] for x in d["experts"]))}</span></a>'
        for s, d in models.items())
    chips = '<button class="chip on" data-f="all">全部</button>' + ''.join(
        f'<button class="chip dom-{k}" data-f="{k}"><span class="dot"></span>{v}</button>' for k, v in DOMAINS.items())
    todo = ''.join(
        f'<li><span class="redlink">{e(g)}</span> 被 {"、".join(e(models[r]["title"]) for r in refs)} 引用</li>'
        for g, refs in ghosts.items()) or '<li>暂无待写条目</li>'
    body = f"""<main class="wrap">
<section class="hero"><h1>专家思维的可视化解剖台</h1>
<p>每个模型讲清四件事：从哪来、怎么运转、什么时候用、什么时候失效。全站 {len(models)} 个模型，{len(ghosts)} 个待写；图谱里的颜色代表领域。</p></section>
<div id="home-graph" class="figure home-graph"></div>
<section id="all"><div class="chips">{chips}</div><div class="grid">{cards}</div></section>
<section id="todo"><h2>待写清单</h2><ul class="todo">{todo}</ul></section>
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
        (out / 'index.html').write_text(model_page(d, models), 'utf-8')

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
    (DIST / 'index.html').write_text(index_page(models, ghosts), 'utf-8')
    print(f'构建完成：{len(models)} 个条目，{len(ghosts)} 个待写 -> {DIST}')


if __name__ == '__main__':
    main()
