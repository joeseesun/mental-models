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
data/roster.json     100 个模型规划清单（slug、领域、切入角度、建议专家）
data/models/*.json   唯一真实来源（含 first-principles 金样板）
tools/mm.py          schema 校验 + 公共读取
tools/gen.py         内容 Agent：add / fix，调 Magpie，校验不过自动带反馈重试 3 轮
tools/batch.py       按 roster 批量生成（--workers 并发，幽灵节点优先，失败落 _failed/ 继续跑）
tools/build.py       data → dist/（首页图谱、条目页、待写清单、graph/search/todo/sitemap/robots）
static/              style.css（领域色 token）+ mm.js（Pele 渲染 Mermaid/ECharts/demo/图谱/弹窗）
dist/                构建产物，rsync 到 VPS /www/wwwroot/mm.qiaomu.ai/
```

## 指令映射

| 指令 | 当前实现 |
|---|---|
| `加：XX` | `python3 tools/gen.py add "XX"`（自动匹配 roster 里的预设角度） |
| `改：XX，……` | `python3 tools/gen.py fix <slug> "……"` |
| 批量补全 | `python3 tools/batch.py`（跳过已有条目） |
| 部署 | `python3 tools/build.py && rsync -az --delete dist/ myvps:/www/wwwroot/mm.qiaomu.ai/` |

## 状态

- 2026-10-22：roster 100 条定稿（物理13 生物15 经济17 心理21 系统16 战略18）。
- 渲染层已换 Pele（obsidianmd/pele），颜色全部走站点 token（--pele-* 映射）。
- 2026-10-21：100 条全部生成完毕（2 条 reasoning 空转失败后单独重试成功；4 处 related 幽灵引用归一到 roster 内条目）。图谱 100 节点 440 边，0 待写，全量校验通过。
- 已上线：https://mm.qiaomu.ai（Nginx 静态 + certbot TLS + Umami，website ID 07f649b7-1176-4d0b-9a02-63d40e21d193）。浏览器已验证：首页图谱、条目页 Pele/ECharts/demo/迷你图、明暗主题、弹窗与页脚链接。
- 开源仓库：https://github.com/joeseesun/mental-models

## 下一步

1. 补渲染校验：headless 打开条目页，抓 `[data-render-error]` 与 console error，失败回喂 Agent。
2. 首页搜索框（search.json 已产出，UI 未做）。
3. PWA 与结构化数据（JSON-LD）有意未做，后续按需补。
