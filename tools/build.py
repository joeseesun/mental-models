#!/usr/bin/env python3
"""静态构建：data/ → dist/。只用标准库；Pele（Mermaid 渲染器）/ ECharts 走 CDN，在浏览器里渲染。

产出：首页（报头 + 今日模型 + 图谱 + 领域分栏 + 人物）、/m/<slug>/ 条目页、/p/<slug>/ 人物页、/p/ 人物索引、
graph.json、search.json、todo.json、sitemap。
数据：data/models/*.json（条目）、data/people/*.json（人物，可缺：缺了就只显示名字不链接）、
data/links/*.json（出处链接，键为 "<slug>#<序号>"，可缺：缺了就给一个搜索链接）。
引用不存在的条目 → 红链（虚线节点），同时进入 dist/todo.json。
"""
import html
import json
import re
import shutil
import sys
from collections import defaultdict
from urllib.parse import quote

from mm import DIST, DOMAINS, ROOT, load_all, validate

STATIC = ROOT / 'static'
LEVEL_LABEL = {'verified': '一手核实', 'secondary': '可靠二手', 'draft': '草稿示意'}
SITE = 'https://mm.qiaomu.ai'
UMAMI_ID = '07f649b7-1176-4d0b-9a02-63d40e21d193'
CDN = ('<script src="https://cdn.jsdelivr.net/npm/pele@1.8.0/dist/pele.global.js"></script>'
       '<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>')
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.cn"><link rel="preconnect" href="https://fonts.gstatic.cn" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.cn/css2?family=Libre+Caslon+Text:ital,wght@0,400;0,700;1,400'
         '&family=Noto+Serif+SC:wght@400;500;600;700&display=swap">')

e = html.escape

MODALS = """<div class="modal" id="reward-modal" hidden><div class="modal-box" role="dialog" aria-modal="true" aria-labelledby="reward-title">
<button class="modal-close" data-close aria-label="关闭">✕</button>
<h3 id="reward-title">请作者喝杯咖啡</h3>
<img class="qr" src="{up}qiaomu_reward_qr.png" alt="打赏二维码" width="220" height="220">
</div></div>
<div class="modal" id="follow-modal" hidden><div class="modal-box" role="dialog" aria-modal="true" aria-labelledby="follow-title">
<button class="modal-close" data-close aria-label="关闭">✕</button>
<h3 id="follow-title">关注向阳乔木</h3>
<img class="qr" src="{up}qiaomu_wechat_public_account_qr.jpg" alt="公众号二维码" width="220" height="220">
<p class="modal-note">公众号：向阳乔木推荐看</p>
<p class="modal-links"><a href="https://github.com/joeseesun/mental-models" target="_blank" rel="noopener">GitHub</a> · <a href="https://x.com/vista8" target="_blank" rel="noopener">X</a></p>
</div></div>"""

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
    'biology': '演化、生态、免疫：生命系统怎么活下去',
    'economics': '激励、稀缺、博弈：资源为什么这样流动',
    'psychology': '偏误、动机、说服：人怎么看、怎么想、怎么选',
    'systems': '反馈、涌现、瓶颈：整体为什么不等于部分之和',
    'strategy': '取舍、护城河、先手：在不确定里下注',
}
# 钩子和原理图永远排前两位；其余按领域气质排：心理先看反例，物理系统先动手，经济战略先看数据
ORDERS = {
    'psychology': ['demo', 'limits', 'evidence', 'howto', 'related', 'sources'],
    'physics': ['demo', 'evidence', 'howto', 'limits', 'related', 'sources'],
    'systems': ['demo', 'evidence', 'howto', 'limits', 'related', 'sources'],
    'economics': ['evidence', 'howto', 'demo', 'limits', 'related', 'sources'],
    'strategy': ['evidence', 'howto', 'demo', 'limits', 'related', 'sources'],
    'biology': ['evidence', 'demo', 'howto', 'limits', 'related', 'sources'],
}
LABELS = {'hook': '场景', 'principle': '原理', 'evidence': '证据', 'demo': '动手',
          'howto': '用法', 'limits': '边界', 'related': '关联', 'sources': '出处'}
PLAY_LABEL = {'gamble': '测测你', 'survivors': '跑一千次', 'chain': '活的模拟'}


def glyph(domain):
    return f'<span class="glyph" aria-hidden="true"><svg viewBox="0 0 100 100">{GLYPHS[domain]}</svg></span>'


def badge(level):
    return f'<span class="lv lv-{level}">{LEVEL_LABEL[level]}</span>'


def page(title, body, desc='', depth=0, extra='', path='', nav=''):
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
{FONTS}<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23111'/%3E%3Ctext x='32' y='46' font-size='38' font-family='serif' font-weight='700' text-anchor='middle' fill='%23fff'%3E思%3C/text%3E%3C/svg%3E"><link rel="stylesheet" href="{up}style.css">{CDN}
<script defer src="https://umami.qiaomu.ai/script.js" data-website-id="{UMAMI_ID}" data-domains="mm.qiaomu.ai"></script></head>
<body data-root="{up}">
<header class="site-header"><div class="wrap header-inner">
<a class="brand" href="{up}index.html">思维模型 Wiki</a>
<nav><a href="{up}index.html#graph" class="{'on' if nav == 'models' else ''}">模型</a><a href="{up}p/index.html" class="{'on' if nav == 'people' else ''}">人物</a></nav>
<button class="chrome-btn" type="button" data-modal-open="reward-modal" aria-label="打赏支持" title="打赏支持">♡</button>
<button class="chrome-btn" type="button" data-modal-open="follow-modal" aria-label="关注向阳乔木" title="关注向阳乔木">✚</button>
<button class="theme-toggle" type="button" data-theme-toggle aria-label="切换明暗主题">◐</button>
</div></header>
{body}
<footer class="site-footer"><div class="wrap">
<div>网页、图谱和视频都从同一份数据生成。出处分三级：一手核实、可靠二手、草稿示意。</div>
<div class="footer-links"><a href="https://github.com/joeseesun/mental-models" target="_blank" rel="noopener">GitHub</a><a href="https://x.com/vista8" target="_blank" rel="noopener">X</a><a href="https://tuijian.qiaomu.ai/" target="_blank" rel="noopener">乔木推荐</a></div>
</div></footer>
{MODALS.format(up=up)}
<script src="{up}mm.js"></script>{extra}
</body></html>"""


# ---------- 数据加载 ----------

def roster_order(models):
    try:
        r = json.loads((ROOT / 'data' / 'roster.json').read_text('utf-8'))['models']
        order = [m['slug'] for m in r if m['slug'] in models]
    except Exception:
        order = []
    return order + [s for s in models if s not in order]


def load_people():
    people, by_name = {}, {}
    d = ROOT / 'data' / 'people'
    if d.exists():
        for p in sorted(d.glob('*.json')):
            if p.name.startswith('_'):
                continue
            x = json.loads(p.read_text('utf-8'))
            x.setdefault('slug', p.stem)
            people[x['slug']] = x
            for n in [x['name']] + x.get('aliases', []):
                by_name[n] = x['slug']
    return people, by_name


def load_links():
    links = {}
    d = ROOT / 'data' / 'links'
    if d.exists():
        for p in sorted(d.glob('*.json')):
            if p.name.startswith('_'):
                continue
            for k, v in json.loads(p.read_text('utf-8')).items():
                url = v if isinstance(v, str) else v.get('url')
                if url and url.startswith('http'):
                    links[k] = url
    return links


def source_link(key, title, links):
    if key in links:
        return f'<a class="go" href="{e(links[key])}" target="_blank" rel="noopener">查看原文 ↗</a>'
    m = re.search(r'《([^》]+)》', title)
    if m:
        return (f'<a class="go find" href="https://search.douban.com/book/subject_search?search_text={quote(m.group(1))}" '
                'target="_blank" rel="noopener">豆瓣搜索 ↗</a>')
    q = quote(re.sub(r'[（(][^）)]*[）)]', '', title)[:80])
    return f'<a class="go find" href="https://cn.bing.com/search?q={q}" target="_blank" rel="noopener">搜索原文 ↗</a>'


def surname(name):
    """人物页水印：取名字最后一段（芒格、塔勒布），最多 3 个字。"""
    last = re.split(r'[·・\s]', name.strip())[-1]
    return last[:4] or name[:2]


def mono(name):
    """人物卡上的大字姓氏：字数越多字号越小，保证一行放得下。"""
    sn = surname(name)
    size = {1: 46, 2: 44, 3: 34, 4: 27}.get(len(sn), 27)
    return f'<span class="mono" style="font-size:{size}px">{e(sn)}</span>'


# ---------- 条目页 ----------

def model_page(d, all_models, order, people_by_name, links):
    s, dom = d['slug'], d['domain']
    idx = order.index(s)
    no = f'№ {idx + 1:03d}'
    ev, demo, play = d['evidence'], d['demo'], d.get('play')

    def expert_chip(x):
        inner = f'<b>{e(x["name"])}</b>{e(x["role"])}'
        slug = people_by_name.get(x['name'])
        return f'<a class="expert" href="../../p/{slug}/">{inner}</a>' if slug else f'<div class="expert">{inner}</div>'
    experts = ''.join(expert_chip(x) for x in d['experts'])
    series_types = {x.get('type') for x in ev['echarts'].get('series', [])}
    single_bar = len(ev['echarts'].get('series', [])) == 1 and series_types == {'bar'}
    n_rel = sum(1 for r in d['related'] if r['slug'] in all_models)

    def sec(key, i, inner):
        cls = ' sources' if key == 'sources' else ''
        return f'<section class="sec{cls}" id="s-{key}"><p class="sec-label">{i:02d} · {LABELS[key]}</p>{inner}</section>'

    def b_hook():
        short = len(d['hook']['story']) < 232
        cls = 'hook-quote' if short else 'hook-prose'
        return f'<h2>{e(d["hook"]["title"])}</h2><div class="{cls}"><p>{e(d["hook"]["story"])}</p></div>'

    def b_principle():
        return ('<h2>一张图看懂它怎么运转</h2><div class="plate"><div class="plate-bar"><span><b>FIG.</b> 原理图</span>'
                f'<span>{e(d["title"])} · {e(d["en"])}</span></div><div id="mermaid"></div>'
                f'<p class="plate-cap">{e(d["principle"]["caption"])}</p></div>')

    def b_evidence():
        h = f'<h2>{e(ev["title"])}{badge(ev["level"])}</h2>'
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
        return f'<h2>照着做，一共 {len(d["howto"])} 步</h2><ol class="steps">{items}</ol>'

    def b_limits():
        if len(d['limits']) <= 4:
            cards = ''.join(
                f'<div class="limit"><p class="sit">{e(r["situation"])}</p>'
                f'<p class="says"><small>模型会说</small>{e(r["model_says"])}</p>'
                f'<p class="real"><small>现实是</small>{e(r["reality"])}</p></div>' for r in d['limits'])
            return f'<h2>什么时候它会坑你</h2><div class="limit-cards">{cards}</div>'
        rows = ''.join(f'<tr><td>{e(r["situation"])}</td><td>{e(r["model_says"])}</td><td>{e(r["reality"])}</td></tr>' for r in d['limits'])
        return ('<h2>什么时候它会坑你</h2><div class="table-wrap"><table class="limits"><thead><tr><th>情境</th><th>模型会说</th><th>现实是</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div>')

    def b_related():
        cards = ''
        for r in d['related']:
            if r['slug'] in all_models:
                t = all_models[r['slug']]
                cards += (f'<a class="rel-card dom-{t["domain"]}" href="../{r["slug"]}/"><b><span class="dot"></span>{e(t["title"])}</b>'
                          f'<span>{e(r["relation"])}</span></a>')
            else:
                cards += f'<div class="rel-card"><b><span class="redlink" title="待写">{e(r["slug"])}</span></b><span>{e(r["relation"])}</span></div>'
        prev_s = order[idx - 1] if idx > 0 else None
        next_s = order[idx + 1] if idx + 1 < len(order) else None
        pager = '<div class="pager">' + (
            f'<a href="../{prev_s}/"><small>← 上一个</small><b>{e(all_models[prev_s]["title"])}</b></a>' if prev_s else '<span></span>') + (
            f'<a href="../{next_s}/"><small>下一个 →</small><b>{e(all_models[next_s]["title"])}</b></a>' if next_s else '<span></span>') + '</div>'
        return f'<h2>顺着这条线，接着读</h2><div id="mini-graph" class="figure mini"></div><div class="rel-grid">{cards}</div><div style="height:34px"></div>{pager}'

    def b_sources():
        items = ''.join(
            f'<li><span>{e(x["title"])}{badge(x["level"])}</span>{source_link(f"{s}#{i}", x["title"], links)}</li>'
            for i, x in enumerate(d['sources']))
        return f'<h2>出处与延伸阅读</h2><ol>{items}</ol>'

    builders = {'hook': b_hook, 'principle': b_principle, 'evidence': b_evidence, 'demo': b_demo,
                'howto': b_howto, 'limits': b_limits, 'related': b_related, 'sources': b_sources}
    rest = list(ORDERS[dom])
    if play:  # 可玩演示紧跟原理图
        rest.remove('demo')
        rest.insert(0, 'demo')
    keys = ['hook', 'principle'] + rest
    body_secs = ''.join(sec(k, i + 1, builders[k]()) for i, k in enumerate(keys))
    toc = ''.join(f'<a href="#s-{k}"><i>{i + 1:02d}</i>{LABELS[k]}</a>' for i, k in enumerate(keys))
    payload = json.dumps({
        'slug': s, 'title': d['title'], 'domain': dom,
        # 横向流程图在窄栏里会被缩到看不清，一律竖排渲染（源数据不动）
        'mermaid': re.sub(r'^(\s*flowchart\s+)LR', r'\1TD', d['principle']['mermaid'], flags=re.M),
        'echarts': ev['echarts'], 'demo': demo, 'play': play,
        'related': [{'slug': r['slug'], 'title': all_models.get(r['slug'], {}).get('title', r['slug']),
                     'domain': all_models.get(r['slug'], {}).get('domain', dom),
                     'exists': r['slug'] in all_models} for r in d['related']],
    }, ensure_ascii=False).replace('</', '<\\/')
    body = f"""<div class="dom-{dom}">
<header class="cover">{glyph(dom)}
<div class="wrap"><div class="cover-inner">
<p class="crumb"><a href="../../index.html">首页</a><span>/</span><a href="../../index.html#d-{dom}">{e(DOMAINS[dom])}</a><span>/</span><span class="no">{no}</span></p>
<h1>{e(d['title'])}</h1><p class="en">{e(d['en'])}</p>
<p class="tagline">{e(d['tagline'])}</p>
<div class="experts">{experts}</div>
</div></div></header>
<div class="wrap layout"><aside class="toc"><p class="label h">本页内容</p>{toc}</aside>
<main class="article">{body_secs}</main></div></div>
<script type="application/json" id="mm-data">{payload}</script>"""
    return page(f'{d["title"]} · 思维模型 Wiki', body, d['tagline'], depth=2, path=f'm/{s}/',
                extra='<script src="../../play.js"></script>' if play else '', nav='models')


# ---------- 人物页 ----------

def person_dom(p, usage):
    ms = usage.get(p['slug'], [])
    return ms[0][1]['domain'] if ms else 'strategy'


def person_page(p, usage):
    ms = usage.get(p['slug'], [])
    dom = person_dom(p, usage)
    pills = ''.join(f'<span>{e(x)}</span>' for x in ([p.get('years', '')] + p.get('identity', [])) if x)
    story = ''.join(f'<p>{e(x)}</p>' for x in p.get('story', []))
    facts = ''.join(f'<div><b>{i:02d}</b>{e(f["text"])}</div>' for i, f in enumerate(p.get('facts', []), 1))
    tl = ''.join(f'<li><b>{e(t["year"])}</b><span>{e(t["text"])}</span></li>' for t in p.get('timeline', []))
    mods = ''.join(
        f'<a class="mlink dom-{m["domain"]}" href="../../m/{m["slug"]}/"><b><span class="dot"></span>{e(m["title"])}</b><span>{e(role)}</span></a>'
        for role, m in ms)
    works = ''.join(f'<li>{e(w["title"])}<em>{e(w.get("year", ""))}</em></li>' for w in p.get('works', []))
    parts = [f'<div class="pstory">{story}</div>']
    if facts:
        parts.append(f'<div class="pstory"><h2>你可能不知道</h2></div><div class="facts-list">{facts}</div>')
    if tl:
        parts.append(f'<div class="pstory"><h2>人生年表</h2></div><ul class="timeline">{tl}</ul>')
    if p.get('thinking'):
        parts.append(f'<div class="pstory"><h2>他怎么想问题</h2><p>{e(p["thinking"])}</p></div>')
    body = f"""<div class="dom-{dom}"><header class="pcover"><span class="big" aria-hidden="true">{e(surname(p['name']))}</span>
<div class="wrap"><div class="cover-inner">
<p class="crumb"><a href="../../index.html">首页</a><span>/</span><a href="../index.html">人物</a><span>/</span><span class="no">{e(DOMAINS[dom])}</span></p>
<h1>{e(p['name'])}</h1><p class="en">{e(p.get('en', ''))}</p>
<p class="epi">{e(p.get('epithet', ''))}</p><div class="pmeta">{pills}</div>
</div></div></header>
<div class="wrap pbody"><main>{''.join(parts)}</main>
<aside class="aside"><div class="blk"><h3>他的思维模型</h3>{mods}</div>
{'<div class="blk"><h3>代表作</h3><ul class="works">' + works + '</ul></div>' if works else ''}</aside></div></div>"""
    return page(f'{p["name"]} · 思维模型 Wiki', body, p.get('epithet', ''), depth=2, path=f'p/{p["slug"]}/', nav='people')


def people_index(people, usage):
    secs = ''
    for k, v in DOMAINS.items():
        ps = [p for p in people.values() if person_dom(p, usage) == k and usage.get(p['slug'])]
        if not ps:
            continue
        cards = ''.join(
            f'<a class="pcard dom-{k}" href="{p["slug"]}/">{mono(p["name"])}<b>{e(p["name"])}</b>'
            f'<span>{e(p.get("epithet", ""))}</span></a>' for p in ps)
        secs += (f'<section class="domain-sec dom-{k}"><div class="domain-head">{glyph(k)}<div><h2>{v}</h2></div>'
                 f'<span class="n">{len(ps)} 人</span></div><div class="people-strip" style="margin-top:22px">{cards}</div></section>')
    body = f"""<main class="wrap people-index"><header class="masthead"><p class="issue">PEOPLE</p><h1>人物</h1>
<p class="sub">{len(people)} 位思想的提出者与推动者</p></header><hr class="rule">{secs or '<p class="empty">人物档案正在整理中</p>'}</main>"""
    return page('人物 · 思维模型 Wiki', body, '思维模型背后的人和他们的故事', depth=1, path='p/', nav='people')


# ---------- 首页 ----------

def index_page(models, ghosts, order, people, usage):
    def card(s):
        d = models[s]
        by = '、'.join(x['name'] for x in d['experts'])
        return (f'<a class="card dom-{d["domain"]}" data-domain="{d["domain"]}" data-q="{e(d["title"] + d["en"] + d["tagline"] + by).lower()}" '
                f'data-slug="{s}" data-title="{e(d["title"])}" data-en="{e(d["en"])}" data-tag="{e(d["tagline"])}" data-no="№ {order.index(s) + 1:03d}" '
                f'data-by="{e(by)}" href="m/{s}/">'
                f'{glyph(d["domain"])}<span class="no">№ {order.index(s) + 1:03d}</span>'
                f'<h3>{e(d["title"])}</h3><div class="en">{e(d["en"])}</div><p>{e(d["tagline"])}</p>'
                f'<span class="who">{e(by)}</span></a>')
    secs = ''
    for k, v in DOMAINS.items():
        ms = [s for s in order if models[s]['domain'] == k]
        secs += (f'<section class="domain-sec dom-{k}" id="d-{k}" data-domain-sec="{k}"><div class="domain-head">{glyph(k)}'
                 f'<div><h2>{v}</h2><p>{DOMAIN_INTRO[k]}</p></div><span class="n">{len(ms)} 个模型</span></div>'
                 f'<div class="grid">{"".join(card(s) for s in ms)}</div></section>')
    tabs = '<a class="tab on" href="#all" data-f="all">全部</a>' + ''.join(
        f'<a class="tab dom-{k}" href="#d-{k}" data-f="{k}">{v}</a>' for k, v in DOMAINS.items())
    legend = ''.join(f'<a class="dom-{k}" href="#d-{k}"><span class="dot"></span>{v}</a>' for k, v in DOMAINS.items())
    first = models[order[0]]
    todo = ''.join(
        f'<li><span class="redlink">{e(g)}</span> 被 {"、".join(e(models[r]["title"]) for r in refs)} 引用</li>'
        for g, refs in ghosts.items())
    todo_sec = f'<section class="domain-sec" id="todo"><div class="sec-head"><h2>待写清单</h2></div><ul class="todo">{todo}</ul></section>' if todo else ''
    n_links = sum(len(d['related']) for d in models.values())
    ranked = sorted((p for p in people.values() if usage.get(p['slug'])), key=lambda p: (-len(usage[p['slug']]), p['slug']))[:12]
    people_sec = ''
    if ranked:
        pc = ''.join(f'<a class="pcard dom-{person_dom(p, usage)}" href="p/{p["slug"]}/">{mono(p["name"])}'
                     f'<b>{e(p["name"])}</b><span>{e(p.get("epithet", ""))}</span></a>' for p in ranked)
        people_sec = (f'<section id="people"><div class="sec-head"><h2>背后的人</h2><span>{len(people)} 位</span></div>'
                      f'<div class="people-strip">{pc}</div><a class="more" href="p/index.html">浏览全部人物 →</a></section>')
    body = f"""<main class="wrap" id="all">
<header class="masthead"><p class="issue">MENTAL MODELS · 向阳乔木</p>
<h1>思维模型 <i>Wiki</i></h1>
<p class="sub">{len(models)} 个模型 · {len(DOMAINS)} 门学科 · {n_links} 条关联</p></header>
<hr class="rule">
<div class="toolbar" id="toolbar"><div class="search"><svg viewBox="0 0 20 20"><circle cx="9" cy="9" r="6"/><path d="M14 14l4 4"/></svg><input id="q" type="search" placeholder="搜模型、英文名、人名，比如「芒格」" autocomplete="off" aria-label="搜索"><kbd>/</kbd></div>
<nav class="tabs">{tabs}</nav></div>
<section class="lead dom-{first['domain']}" id="today">
<a class="lead-art" href="m/{order[0]}/">{glyph(first['domain'])}<span class="no">今日模型 · № 001</span><span class="nm">{e(first['title'])}</span></a>
<div class="lead-text"><p class="kicker">今日模型</p><h2>{e(first['title'])}</h2><div class="en">{e(first['en'])}</div>
<p>{e(first['tagline'])}</p><div class="by">{e('、'.join(x['name'] for x in first['experts']))}</div>
<a class="btn-line" href="m/{order[0]}/">开始阅读 →</a></div></section>
<section id="graph"><div class="sec-head" style="padding-top:48px"><h2>知识图谱</h2><span>点击节点进入 · 滚轮缩放 · 可拖动</span></div>
<div id="home-graph" class="home-graph"></div><div class="legend">{legend}</div></section>
{secs}<p class="empty" id="empty" hidden>没有找到匹配的模型</p>
{people_sec}
{todo_sec}
</main>"""
    return page('思维模型 Wiki', body, '用图讲清全球专家的思维框架', nav='models')


def main():
    models = load_all()
    bad = {s: validate(d, models) for s, d in models.items()}
    bad = {s: p for s, p in bad.items() if p}
    if bad:
        for s, p in bad.items():
            print(f'[校验失败] {s}', *p, sep='\n  - ')
        sys.exit(1)
    order = roster_order(models)
    people, by_name = load_people()
    links = load_links()
    usage = defaultdict(list)  # 人物 slug → [(他在该模型里的角色, 模型)]
    for s in order:
        for x in models[s]['experts']:
            if x['name'] in by_name:
                usage[by_name[x['name']]].append((x['role'], models[s]))

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
        (out / 'index.html').write_text(model_page(d, models, order, by_name, links), 'utf-8')
    (DIST / 'p').mkdir(exist_ok=True)
    for slug, p in people.items():
        out = DIST / 'p' / slug
        out.mkdir(parents=True)
        (out / 'index.html').write_text(person_page(p, usage), 'utf-8')
    (DIST / 'p' / 'index.html').write_text(people_index(people, usage), 'utf-8')

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
        + ''.join(f'<url><loc>{SITE}/p/{s}/</loc><lastmod>{today}</lastmod></url>\n' for s in people)
        + '</urlset>\n', 'utf-8')
    (DIST / 'robots.txt').write_text(
        'User-agent: *\nAllow: /\n'
        f'Sitemap: {SITE}/sitemap.xml\n', 'utf-8')
    (DIST / 'index.html').write_text(index_page(models, ghosts, order, people, usage), 'utf-8')
    print(f'构建完成：{len(models)} 个条目，{len(people)} 位人物，{len(links)} 条出处直链，{len(ghosts)} 个待写 -> {DIST}')


if __name__ == '__main__':
    main()
