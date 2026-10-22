#!/usr/bin/env python3
"""单文件校验，供内容工作者自查：python3 tools/check.py [slug ...]；不带参数则校验全部条目。"""
import sys
from mm import load_all, validate

models = load_all()
slugs = sys.argv[1:] or list(models)
bad = 0
for s in slugs:
    p = validate(models[s], models)
    if p:
        bad += 1
        print(f'[不通过] {s}', *p, sep='\n  - ')
print(f'校验 {len(slugs)} 个，{bad} 个不通过')
sys.exit(1 if bad else 0)
