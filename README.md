# 思维模型 Wiki

专家思维的可视化解剖台。收集整理全球 100 个顶级思维模型，每个模型讲清四件事：从哪来、怎么运转、什么时候用、什么时候失效。

在线阅读：<https://mm.qiaomu.ai>

## 每个条目包含 8 个区块

| 区块 | 内容 |
|---|---|
| 场景钩子 | 一个具体的真实故事 |
| 原理图 | Mermaid 流程图（由 [Pele](https://github.com/obsidianmd/pele) 渲染） |
| 数据证据 | ECharts 图表，数据分三级标注：一手核实 / 可靠二手 / 草稿示意 |
| 交互演示 | 拖滑块看模型参数如何改变结果 |
| 怎么用 | 3~5 步操作清单 |
| 失效边界 | 模型什么时候会坑人（反例对比表） |
| 关联模型 | 与其他模型的连接，构成一张 100 节点的知识图谱 |
| 出处 | 可核对的来源列表 |

## 架构

纯静态、零 Node 依赖，Python 标准库构建，Mermaid / ECharts 走 CDN 在浏览器端渲染。

```
data/roster.json     100 个模型的规划清单（slug、领域、切入角度）
data/models/*.json   唯一真实来源，每个文件一个条目
data/models/first-principles.json   手写金样板
tools/mm.py          schema 校验（唯一真实来源的守门人）
tools/gen.py         内容生成 Agent：add / fix，校验不过自动带反馈重试
tools/batch.py       批量生成：按 roster 逐条生成，3 并发
tools/build.py       data → dist/（首页图谱、条目页、graph/search/todo.json）
static/              style.css（领域色 token + 明暗主题）+ mm.js（运行时渲染）
dist/                构建产物（可直接静态托管）
```

## 本地开发

```bash
python3 tools/build.py          # 构建
cd dist && python3 -m http.server 8000   # 预览
```

## 如何新增一个条目

`data/models/*.json` 是唯一真实来源。改 JSON 后重新 `build.py` 即可，校验不过会拦截构建。

用 LLM 辅助生成（需配置 Magpie API）：

```bash
python3 tools/gen.py add "锚定效应"        # 自动匹配 roster 里的预设角度
python3 tools/gen.py fix anchoring "换个故事"   # 局部修改
```

生成内容有硬约束：禁止自带颜色（由站点 token 统一注入，保证明暗主题一致）、禁止破折号、demo 表达式白名单、数据必须标注可信级别。

## 领域分布

物理 13 · 生物 15 · 经济 17 · 心理 21 · 系统 16 · 战略 18，共 100 个。

## License

[MIT](LICENSE)
