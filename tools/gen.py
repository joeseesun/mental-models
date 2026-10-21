#!/usr/bin/env python3
"""内容生成 Agent：一句指令 → 校验通过的 model.json。

用法：
  python3 tools/gen.py add "红皇后效应"            # 新增条目
  python3 tools/gen.py add "红皇后效应" --domain biology --slug red-queen-effect
  python3 tools/gen.py fix first-principles "加 SpaceX 成本数据图"   # 局部修改，整条回写前再校验

模型走 Magpie 的 bigmodel-preview/glm-x-preview-f（思考型路由，必须 16384 预算，否则 reasoning 吃满、正文为空）。
校验不过就把问题清单喂回模型重试，最多 3 轮；仍失败则写入 data/_failed/ 供人工看。
"""
import argparse
import json
import re
import subprocess
import sys
import time

import requests

from mm import DATA, DOMAINS, ROOT, load_all, validate

BASE_URL = 'https://magpie.qiaomu.ai/v1'
MODEL = 'bigmodel-preview/glm-x-preview-f'
MAX_TOKENS = 16384
GOLD = 'first-principles'

SYSTEM = """你是「Mental Models Wiki」的内容生成 Agent。你的产出是一份严格符合 schema 的 JSON，不是文章。
站点定位：专家思维的可视化解剖台。每个模型必须讲清四件事：从哪来、怎么运转、什么时候用、什么时候失效。

硬性规则：
1. 只输出一个 JSON 对象，不要 Markdown 围栏，不要任何解释文字。
2. 所有文本用简体中文，句子短，具体，有真实的人名、年份、数字。禁止使用破折号（— 或 –），用逗号或句号。
3. tagline 不超过 20 个汉字。hook.story 是一个具体真实的故事，不少于 120 字。
4. principle.mermaid 是合法的 Mermaid 源码（flowchart/stateDiagram-v2/sequenceDiagram/mindmap 等），至少 4 行，节点文字用中文，换行用 \\n；
   含括号、冒号、引号的节点文字必须用 ["..."] 包起来；不得出现 style/classDef/linkStyle。
5. evidence.echarts 是合法的 ECharts option，必须有非空 series；不得出现 color/itemStyle/lineStyle/areaStyle/textStyle/backgroundColor（颜色由站点注入）。
   数据必须来自你确信的公开数据或经典研究；不确定就把 evidence.level 设为 draft，并在 source 里写明是示意数据。
   level 含义：verified=一手来源可核对；secondary=可靠二手来源；draft=示意或未核实。
6. demo 是「拖滑块看结果」：params 1~3 个滑块（id 为英文标识符，default 在 min..max 内）；x 是横轴范围；
   series 里每条 expr 是只含 x、滑块 id、数字、+ - * / ( ) 和 Math 函数（pow exp log sin cos min max sqrt abs）的 JS 表达式。
   不要写任何其他变量。
7. howto 3~5 步；limits 至少 3 行（situation / model_says / reality）反例，要诚实写出模型什么时候会坑人。
8. related 至少 2 个，slug 优先从「已有条目」和「规划中条目」里选；允许引用尚未写的新 slug（小写英文连字符），站点会把它显示成待写红链。
9. domain 只能是：physics biology economics psychology systems strategy。
10. 不要照抄示例的内容，只学它的结构和质量水位。
"""


def api_key():
    return subprocess.check_output(
        ['security', 'find-generic-password', '-s', 'qiaomu-llm', '-a', 'magpie', '-w'], text=True).strip()


def chat(messages, timeout=1200):
    last = None
    for attempt in range(4):
        try:
            r = requests.post(f'{BASE_URL}/chat/completions',
                              headers={'Authorization': f'Bearer {api_key()}', 'Content-Type': 'application/json'},
                              json={'model': MODEL, 'messages': messages, 'max_tokens': MAX_TOKENS, 'temperature': 0.6},
                              timeout=timeout)
            if r.status_code in (429,) or r.status_code >= 500:
                last = f'HTTP {r.status_code}: {r.text[:200]}'
                time.sleep(8 * 2 ** attempt)
                continue
            r.raise_for_status()
            m = r.json()['choices'][0]['message']
            if not (m.get('content') or '').strip():
                last = 'reasoning-only，正文为空'
                continue
            return m['content']
        except requests.RequestException as e:
            last = str(e)[:250]
            time.sleep(8 * 2 ** attempt)
    raise RuntimeError(f'模型调用失败：{last}')


def extract_json(text):
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    i, j = text.find('{'), text.rfind('}')
    return json.loads(text[i:j + 1])


def context(existing):
    gold = (DATA / f'{GOLD}.json').read_text('utf-8')
    lst = '\n'.join(f'- {s}: {d["title"]}（{d["domain"]}）' for s, d in existing.items()) or '（暂无）'
    planned = ''
    roster = ROOT / 'data' / 'roster.json'
    if roster.exists():
        models = json.loads(roster.read_text('utf-8'))['models']
        todo = [m for m in models if m['slug'] not in existing]
        if todo:
            plst = '\n'.join(f'- {m["slug"]}: {m["title"]}（{m["domain"]}）' for m in todo)
            planned = f'\n\n规划中条目（related 可以引用它们的 slug，站点会显示为待写红链，全部写完后会自动连上）：\n{plst}'
    return f'已有条目（related 优先从这里选）：\n{lst}{planned}\n\n质量与结构参考示例（只学结构和水位，不要抄内容）：\n{gold}'


def run(messages, slug_hint=None, rounds=3):
    existing = load_all()
    for rd in range(1, rounds + 1):
        raw = chat(messages)
        try:
            d = extract_json(raw)
        except Exception as e:
            problems = [f'输出不是合法 JSON：{e}']
            d = None
        else:
            if slug_hint:
                d['slug'] = slug_hint
            problems = validate(d, existing)
        if not problems:
            return d, []
        print(f'第 {rd} 轮校验未过（{len(problems)} 项）：', *problems[:6], sep='\n  - ', flush=True)
        messages = messages + [
            {'role': 'assistant', 'content': raw},
            {'role': 'user', 'content': '校验未通过，请修正后重新输出完整 JSON（仍只输出 JSON）：\n' + '\n'.join(f'- {p}' for p in problems)},
        ]
    return d, problems


def save(d, problems):
    if problems:
        fd = ROOT / 'data' / '_failed'
        fd.mkdir(exist_ok=True)
        p = fd / f'{(d or {}).get("slug", "unknown")}.json'
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), 'utf-8')
        print('失败，已写入', p)
        sys.exit(1)
    p = DATA / f'{d["slug"]}.json'
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print('已写入', p)


def roster_lookup(name=None, slug=None):
    """按 slug 或标题在规划清单里找预设条目。"""
    roster = ROOT / 'data' / 'roster.json'
    if not roster.exists():
        return None
    for m in json.loads(roster.read_text('utf-8'))['models']:
        if (slug and m['slug'] == slug) or (name and m['title'] == name):
            return m
    return None


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('add')
    a.add_argument('name')
    a.add_argument('--domain', choices=list(DOMAINS))
    a.add_argument('--slug')
    f = sub.add_parser('fix')
    f.add_argument('slug')
    f.add_argument('instruction')
    args = ap.parse_args()

    ctx = context(load_all())
    if args.cmd == 'add':
        hint = roster_lookup(args.name, args.slug) or {}
        ask = f'请为思维模型「{args.name}」生成完整条目。'
        if hint.get('en'):
            ask += f'英文名 {hint["en"]}。'
        domain = args.domain or hint.get('domain')
        slug = args.slug or hint.get('slug')
        if domain:
            ask += f' domain 用 {domain}。'
        if slug:
            ask += f' slug 用 {slug}。'
        if hint.get('note'):
            ask += f'建议切入角度：{hint["note"]}。'
        if hint.get('experts'):
            ask += '建议专家：' + '、'.join(hint['experts']) + '。'
        msgs = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': ctx + '\n\n' + ask}]
        d, probs = run(msgs, slug)
    else:
        old = (DATA / f'{args.slug}.json').read_text('utf-8')
        msgs = [{'role': 'system', 'content': SYSTEM},
                {'role': 'user', 'content': f'{ctx}\n\n现有条目如下：\n{old}\n\n修改要求：{args.instruction}\n只改相关字段，其余原样保留，输出修改后的完整 JSON。'}]
        d, probs = run(msgs, args.slug)
    save(d, probs)


if __name__ == '__main__':
    main()
