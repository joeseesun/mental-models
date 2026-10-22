#!/usr/bin/env python3
"""Mental Models Wiki 公共层：路径、读取全部条目、schema 校验（唯一真实来源的守门人）。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'models'
DIST = ROOT / 'dist'

DOMAINS = {
    'physics': '物理', 'biology': '生物', 'economics': '经济',
    'psychology': '心理', 'systems': '系统', 'strategy': '战略',
}
PLAY_KINDS = ('gamble', 'survivors', 'chain')  # 可玩演示的组件类型，对应 static/play.js
LEVELS = ('verified', 'secondary', 'draft')
SLUG_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
# demo 表达式白名单：只允许 x、参数 id、数字、运算符、括号、Math.xxx
EXPR_RE = re.compile(r'^[\w\s.+\-*/%(),<>=?:!&|]*$')
DASH_RE = re.compile('[—–]')


def load_all():
    out = {}
    for p in sorted(DATA.glob('*.json')):
        d = json.loads(p.read_text('utf-8'))
        out[d.get('slug', p.stem)] = d
    return out


def _strip_colors(o, path, problems):
    """ECharts 配置不得自带颜色，统一由站点 token 注入。"""
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ('color', 'itemStyle', 'lineStyle', 'areaStyle', 'backgroundColor', 'textStyle'):
                problems.append(f'{path}.{k} 不允许写样式/颜色（由站点 token 统一注入）')
            else:
                _strip_colors(v, f'{path}.{k}', problems)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            _strip_colors(v, f'{path}[{i}]', problems)


def validate(d, known_slugs=()):
    """返回问题列表；空列表 = 通过。"""
    P = []
    def need(obj, key, typ, path):
        if not isinstance(obj, dict) or key not in obj:
            P.append(f'缺少字段 {path}{key}')
            return None
        if not isinstance(obj[key], typ):
            P.append(f'{path}{key} 类型应为 {typ.__name__}')
            return None
        return obj[key]

    slug = need(d, 'slug', str, '')
    if slug and not SLUG_RE.match(slug):
        P.append('slug 只能是小写字母数字加连字符')
    need(d, 'title', str, '')
    need(d, 'en', str, '')
    dom = need(d, 'domain', str, '')
    if dom and dom not in DOMAINS:
        P.append(f'domain 必须是 {list(DOMAINS)} 之一')
    experts = need(d, 'experts', list, '')
    if experts is not None and not experts:
        P.append('experts 至少 1 人')
    for e in experts or []:
        need(e, 'name', str, 'experts[].')
        need(e, 'role', str, 'experts[].')
    tag = need(d, 'tagline', str, '')
    if tag and len(tag) > 20:
        P.append(f'tagline 超过 20 字（{len(tag)}）')

    hook = need(d, 'hook', dict, '')
    if hook:
        need(hook, 'title', str, 'hook.')
        s = need(hook, 'story', str, 'hook.')
        if s and len(s) < 120:
            P.append('hook.story 太短（<120 字），要一个具体的真实故事')

    pr = need(d, 'principle', dict, '')
    if pr:
        m = need(pr, 'mermaid', str, 'principle.')
        need(pr, 'caption', str, 'principle.')
        if m is not None:
            if not re.match(r'^\s*(flowchart|graph|sequenceDiagram|stateDiagram-v2|mindmap|timeline|quadrantChart)\b', m):
                P.append('principle.mermaid 必须以 flowchart/graph/sequenceDiagram/stateDiagram-v2/mindmap/timeline/quadrantChart 开头')
            if '```' in m:
                P.append('principle.mermaid 不要带 ``` 围栏')
            if re.search(r'\b(style|classDef|linkStyle)\b', m):
                P.append('principle.mermaid 不允许 style/classDef/linkStyle（颜色由站点 token 注入）')
            if m.count('\n') < 3:
                P.append('principle.mermaid 太简单（<4 行）')

    ev = need(d, 'evidence', dict, '')
    if ev:
        need(ev, 'title', str, 'evidence.')
        need(ev, 'takeaway', str, 'evidence.')
        opt = need(ev, 'echarts', dict, 'evidence.')
        lv = need(ev, 'level', str, 'evidence.')
        if lv and lv not in LEVELS:
            P.append(f'evidence.level 必须是 {LEVELS}')
        need(ev, 'source', str, 'evidence.')
        if opt is not None:
            if not isinstance(opt.get('series'), list) or not opt['series']:
                P.append('evidence.echarts.series 必须是非空数组')
            _strip_colors(opt, 'evidence.echarts', P)

    demo = need(d, 'demo', dict, '')
    if demo:
        need(demo, 'title', str, 'demo.')
        need(demo, 'takeaway', str, 'demo.')
        params = need(demo, 'params', list, 'demo.')
        ids = set()
        for p in params or []:
            for k in ('id', 'label', 'min', 'max', 'step', 'default'):
                if k not in p:
                    P.append(f'demo.params[] 缺少 {k}')
            if 'id' in p:
                ids.add(p['id'])
            if all(k in p for k in ('min', 'max', 'default')) and not (p['min'] <= p['default'] <= p['max']):
                P.append(f'demo.params[{p.get("id")}] default 不在 min..max 内')
        if params is not None and not (1 <= len(params) <= 3):
            P.append('demo.params 需要 1 到 3 个滑块')
        x = need(demo, 'x', dict, 'demo.')
        if x:
            for k in ('label', 'from', 'to', 'step'):
                if k not in x:
                    P.append(f'demo.x 缺少 {k}')
        ser = need(demo, 'series', list, 'demo.')
        for s in ser or []:
            need(s, 'name', str, 'demo.series[].')
            ex = need(s, 'expr', str, 'demo.series[].')
            if ex is not None:
                if not EXPR_RE.match(ex):
                    P.append(f'demo 表达式含非法字符：{ex}')
                for w in re.findall(r'[A-Za-z_]\w*', ex):
                    if w not in ids and w not in ('x', 'Math', 'sin', 'cos', 'exp', 'log', 'pow', 'min', 'max', 'sqrt', 'abs', 'PI', 'E', 'log2', 'log10', 'floor', 'ceil', 'round'):
                        P.append(f'demo 表达式使用了未声明的变量 {w}')

    how = need(d, 'howto', list, '')
    if how is not None and not (3 <= len(how) <= 5):
        P.append('howto 需要 3 到 5 步')
    for h in how or []:
        need(h, 'step', str, 'howto[].')
        need(h, 'detail', str, 'howto[].')

    lim = need(d, 'limits', list, '')
    if lim is not None and len(lim) < 3:
        P.append('limits 至少 3 行反例对比')
    for r in lim or []:
        for k in ('situation', 'model_says', 'reality'):
            need(r, k, str, 'limits[].')

    rel = need(d, 'related', list, '')
    for r in rel or []:
        need(r, 'slug', str, 'related[].')
        need(r, 'relation', str, 'related[].')
    if rel is not None and len(rel) < 2:
        P.append('related 至少 2 个')

    src = need(d, 'sources', list, '')
    if src is not None and not src:
        P.append('sources 至少 1 条')
    for s in src or []:
        need(s, 'title', str, 'sources[].')
        lv = need(s, 'level', str, 'sources[].')
        if lv and lv not in LEVELS:
            P.append(f'sources[].level 必须是 {LEVELS}')

    # 全文禁破折号（沿用 lex 站的写作规范）
    blob = json.dumps({k: v for k, v in d.items() if k != 'principle'}, ensure_ascii=False)
    if DASH_RE.search(blob):
        P.append('文本中出现破折号，请改用逗号或句号')
    drill = d.get('drill')
    if drill is not None:
        if not isinstance(drill, list) or not 3 <= len(drill) <= 4:
            P.append('drill 需要 3 到 4 道题')
        else:
            for i, q in enumerate(drill):
                if not all(isinstance(q.get(k), str) and q[k] for k in ('scene', 'ask', 'explain')):
                    P.append(f'drill[{i}] 缺少 scene/ask/explain')
                o = q.get('options')
                if not isinstance(o, list) or not 3 <= len(o) <= 4 or not isinstance(q.get('answer'), int) or not 0 <= q['answer'] < len(o):
                    P.append(f'drill[{i}] options 需 3 到 4 项且 answer 在范围内')
    play = d.get('play')
    if play is not None:
        if not isinstance(play, dict) or play.get('kind') not in PLAY_KINDS:
            P.append(f'play.kind 必须是 {list(PLAY_KINDS)} 之一')
        else:
            need(play, 'title', str, 'play.')
            need(play, 'takeaway', str, 'play.')
    return P
