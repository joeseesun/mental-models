# Mental Models Wiki 落地框架

基于 lex 站实际结构（`tools/build.py` 单脚本构建、纯静态、`tools/gen_zh.py` 走 Magpie 批产、CSS token 明暗主题）调整原方案。

## 与原方案的差异

| 原方案 | 实际 | 原因 |
|---|---|---|
| `model.json` + `body.mdx` | **单文件 `data/models/<slug>.json`**，8 区块全是字段 | lex 构建零依赖（纯 Python 标准库），MDX 要引入 Node 工具链；单文件也让校验与视频派生更直接 |
| Pagefind 搜索 | 先出 `search.json`，后续接 lex 现成的 `app.js` 搜索 | 条目少时没必要引入二进制依赖 |
| 校验 = schema + 渲染 | 现已有 schema 校验（`tools/mm.py`）；渲染校验待补（headless 浏览器渲染 Mermaid/ECharts） | 渲染校验第 2 周的核心 |
| 颜色 | 生成内容禁止自带颜色（校验器拦截 color/itemStyle 等） | 保证 Mermaid、ECharts 共用站点 token |

## 目录

```
data/models/*.json   唯一真实来源（含 first-principles 金样板）
tools/mm.py          schema 校验 + 公共读取
tools/gen.py         内容 Agent：add / fix，调 Magpie bigmodel-preview/glm-x-preview-f，校验不过自动带反馈重试 3 轮
tools/build.py       data → dist/（首页图谱、条目页、待写清单、graph/search/todo.json）
static/              style.css（领域色 token）+ mm.js（Pele 渲染 Mermaid/ECharts/demo/图谱运行时渲染，颜色走 --pele-* 映射站点 token）
```

## 指令映射

| 指令 | 当前实现 |
|---|---|
| `加：XX` | `python3 tools/gen.py add "XX" [--domain d --slug s]` |
| `改：XX，……` | `python3 tools/gen.py fix <slug> "……"` |
| 加专家 / 加场景 | 待做：新增 `data/experts`、`data/scenes` schema，条目页反向聚合 |
| 视频 | 待做：`tools/video.py` 读 json 出 HyperFrames 工程 |

## 下一步

1. 人工审 3 篇样板（first-principles 手写金样板，six-thinking-hats、red-queen-effect 由 glm 生成），定下限。
2. 补渲染校验：headless 打开条目页，抓 `[data-render-error]` 与 console error，失败回喂 Agent。
3. 把 `gen.py` 封装为 skill `qiaomu-mm`（用 qiaomu-meta-skill 创建）。
4. 批量 30 篇走 PR；部署 Cloudflare Pages。
