#!/usr/bin/env python3
"""出处链接核实：对 data/links/_queue-*.json 里的每条出处，用 Crossref / Google Books 公开接口查找，
只有标题词与出处原文高度吻合才采信，写入 data/links/resolved.json（键 "<slug>#<序号>"）。
查不到的不写，页面会退回到「搜索原文」链接，绝不放猜出来的链接。
用法：python3 tools/resolve_links.py"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from mm import ROOT

STOP = set('a an the of and in on for to by with from at as its is are into over under between within via'.split())
UA = 'mental-models-wiki/1.0 (mailto:joe@32kw.com)'


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def toks(s):
    return [w for w in re.findall(r'[a-z0-9]+', s.lower()) if w not in STOP]


def latin(text):
    return re.sub(r'[　-鿿＀-￯]+', ' ', text)


def year_of(text):
    m = re.findall(r'(1[5-9]\d\d|20[0-2]\d)', text)
    return int(m[-1]) if m else None


NOISE = ('reflections on', 'comment on', 'comments on', 'reply to', 'erratum', 'correction', 'review of', 'in memoriam')


def cjk_share(text):
    cjk = len(re.findall(r'[\u3000-\u9fff\uff00-\uffef]', text))
    return cjk / max(1, len(text))


def acceptable(title, text):
    """过滤掉评论、勘误，以及中文占比过高、拉丁字只是附注的出处（容易配到同名的别的东西）。"""
    return not title.lower().startswith(NOISE) and cjk_share(text) <= 0.5


def covered(title, text):
    t = toks(title)
    if len(t) < 3:
        return 0
    pool = set(toks(text))
    return sum(1 for w in t if w in pool) / len(t)


def via_crossref(text):
    q = latin(text).strip()
    if len(toks(q)) < 4:
        return None
    d = get('https://api.crossref.org/works?rows=3&select=DOI,title,issued,URL&query.bibliographic=' + urllib.parse.quote(q))
    if not d:
        return None
    y = year_of(text)
    for it in d['message']['items']:
        title = (it.get('title') or [''])[0]
        iy = (it.get('issued', {}).get('date-parts') or [[None]])[0][0]
        if covered(title, q) >= 0.8 and acceptable(title, text) and (y is None or iy is None or abs(iy - y) <= 1):
            return {'url': 'https://doi.org/' + it['DOI'], 'via': 'crossref', 'matched': title}
    return None


def via_books(text):
    q = latin(text).strip()
    if len(toks(q)) < 3 or '《' in text and len(toks(q)) < 4:
        return None
    d = get('https://www.googleapis.com/books/v1/volumes?maxResults=3&q=' + urllib.parse.quote(re.sub(r'\([^)]*\)', ' ', q)[:120]))
    if not d:
        return None
    y = year_of(text)
    for it in d.get('items', []):
        v = it['volumeInfo']
        title = v.get('title', '')
        iy = re.match(r'\d{4}', v.get('publishedDate', '') or '')
        if covered(title, q) >= 0.8 and acceptable(title, text) and len(toks(title)) >= 3:
            return {'url': v.get('infoLink', '').replace('http://', 'https://'), 'via': 'books', 'matched': title}
    return None


def resolve(item):
    t = item['title']
    r = via_crossref(t) or via_books(t)
    return item['key'], r


def main():
    items = []
    for p in sorted((ROOT / 'data' / 'links').glob('_queue-*.json')):
        items += json.loads(p.read_text('utf-8'))
    out_p = ROOT / 'data' / 'links' / 'resolved.json'
    out = json.loads(out_p.read_text('utf-8')) if out_p.exists() else {}
    todo = [i for i in items if i['key'] not in out]
    print(f'待查 {len(todo)} 条')
    with ThreadPoolExecutor(6) as ex:
        for n, (k, r) in enumerate(ex.map(resolve, todo), 1):
            if r and r['url']:
                out[k] = r
            if n % 40 == 0:
                print(n, len(out), flush=True)
                out_p.write_text(json.dumps(out, ensure_ascii=False, indent=1), 'utf-8')
    out_p.write_text(json.dumps(out, ensure_ascii=False, indent=1), 'utf-8')
    print(f'完成：命中 {len(out)} / {len(items)}')


if __name__ == '__main__':
    main()
