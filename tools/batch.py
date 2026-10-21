#!/usr/bin/env python3
"""批量生成 roster.json 里尚未完成的条目。

用法：
  python3 tools/batch.py --limit 2     # 冒烟：只跑前 2 个
  python3 tools/batch.py               # 全量：跳过已有条目，剩余全部
  python3 tools/batch.py --workers 4   # 并发数（默认 3，太高容易触发限流）

被已有条目 related 引用的幽灵 slug 优先生成。每条失败自动带反馈重试 3 轮
（复用 gen.run），仍失败写入 data/_failed/ 并继续跑后面的；结束时汇总。
"""
import argparse
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gen import SYSTEM, context, extract_json, run
from mm import DATA, ROOT, load_all, validate

ROSTER = ROOT / 'data' / 'roster.json'
FAILED = ROOT / 'data' / '_failed'
_log_lock = threading.Lock()


def log(msg):
    with _log_lock:
        print(msg, flush=True)


def generate_one(m):
    slug = m['slug']
    existing = load_all()
    ask = (f'请为思维模型「{m["title"]}」（{m["en"]}）生成完整条目。'
           f'domain 用 {m["domain"]}，slug 用 {slug}。'
           f'建议切入角度：{m["note"]}。'
           f'建议专家：{"、".join(m["experts"])}。')
    msgs = [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': context(existing) + '\n\n' + ask}]
    d, probs = run(msgs, slug)
    if probs:
        FAILED.mkdir(exist_ok=True)
        (FAILED / f'{slug}.json').write_text(
            json.dumps(d, ensure_ascii=False, indent=2), 'utf-8')
        return slug, False, probs
    (DATA / f'{slug}.json').write_text(
        json.dumps(d, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    return slug, True, []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--limit', type=int, default=0, help='只跑前 N 个（冒烟用）')
    args = ap.parse_args()

    roster = json.loads(ROSTER.read_text('utf-8'))['models']
    existing = load_all()
    todo = [m for m in roster if m['slug'] not in existing]
    ghosts = {r['slug'] for d in existing.values() for r in d['related'] if r['slug'] not in existing}
    todo.sort(key=lambda m: m['slug'] not in ghosts)  # 幽灵节点排最前
    if args.limit:
        todo = todo[:args.limit]
    log(f'待生成 {len(todo)} 条（并发 {args.workers}）：{"、".join(m["slug"] for m in todo[:12])}{" ..." if len(todo) > 12 else ""}')

    ok, bad = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(generate_one, m): m for m in todo}
        for fut in as_completed(futs):
            slug = futs[fut]['slug']
            try:
                s, success, probs = fut.result()
            except Exception as e:
                bad.append((slug, [str(e)[:200]]))
                log(f'[异常] {slug}: {str(e)[:200]}')
                continue
            if success:
                ok.append(s)
                log(f'[完成] {s}（{len(ok)}/{len(todo)}）')
            else:
                bad.append((s, probs))
                log(f'[失败] {s}: {"; ".join(probs[:3])}')

    log(f'--- 结束：成功 {len(ok)}，失败 {len(bad)}')
    if bad:
        for s, probs in bad:
            log(f'  失败 {s}: {"; ".join(probs[:2])}')
        sys.exit(1)


if __name__ == '__main__':
    main()
