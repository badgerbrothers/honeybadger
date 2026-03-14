# Badgers MVP RAG 重构方案

## 1. 文档目的

本文给出一个基于 **当前仓库实际代码结构** 的 RAG 重构方案，目标是解决下面几个问题：

1. `backend/rag` 和 `worker/rag` 存在重复实现
2. 当前公开 RAG API 仍是 stub，没有真正接上实现
3. 项目文件上传没有触发索引
4. worker 执行主链没有真正使用项目 RAG 上下文
5. `backend` 与 `worker` 之间的职责边界还不够清晰

配套文档：

- [current-system-architecture.md](F:/Programs/project_4/docs/current-system-architecture.md)
- [target-architecture-gap-analysis.md](F:/Programs/project_4/docs/target-architecture-gap-analysis.md)
- [architecture-execution-task-list.md](F:/Programs/project_4/docs/architecture-execution-task-list.md)

---

## 2. 结论先行

对当前项目，推荐的 RAG 归属方式是：

- `backend` 负责 **RAG 控制面**
- `worker` 负责 **RAG 执行面**
- 真正的 RAG 核心实现只保留 **一套**

更具体地说：

1. **文件上传入口放 backend**
2. **文档解析、chunk、embedding、索引执行放 worker**
3. **任务执行时的检索放 worker**
4. **用户主动查询的 RAG API 入口放 backend**
5. **底层 parser/chunker/retriever/indexer 不能在 backend 和 worker 各保留一套**

一句话版本：

**入口在 backend，干活在 worker，核心代码只保留一套。**

---

## 3. 当前代码现状

当前仓库里与 RAG 相关的主要文件如下。

## 3.1 Backend 侧

- `backend/rag/chunker.py`
- `backend/rag/embeddings.py`
- `backend/rag/indexer.py`
- `backend/rag/retriever.py`
- `backend/rag/parsers/__init__.py`
- `backend/app/routers/rag.py`
- `backend/app/models/document_chunk.py`

## 3.2 Worker 侧

- `worker/rag/chunker.py`
- `worker/rag/embeddings.py`
- `worker/rag/indexer.py`
- `worker/rag/retriever.py`
- `worker/rag/parsers/base.py`
- `worker/rag/parsers/exceptions.py`
- `worker/rag/parsers/markdown_parser.py`
- `worker/rag/parsers/pdf_parser.py`
- `worker/rag/parsers/txt_parser.py`

## 3.3 当前状态判断

从实现完整度看，`worker/rag` 明显比 `backend/rag` 更适合作为保留基线：

1. `worker/rag/parsers/*` 有更完整的 parser 分层
2. `worker/rag/embeddings.py` 有简单的 retry 逻辑
3. `worker/rag/chunker.py` 对空文本处理更完整
4. `backend/app/routers/rag.py` 当前只是 API 外壳，`index` 和 `search` 仍是 stub

因此：

**不要以 `backend/rag` 作为未来唯一实现。**

---

## 4. 目标职责划分

## 4.1 Backend 负责什么

Backend 应该保留这些 RAG 相关职责：

1. 文件上传入口
2. 文件元数据管理
3. 触发“索引任务”
4. 对前端暴露：
   - chunk 列表
   - RAG 搜索
   - 索引状态（后续可加）

Backend 不应该承担：

1. 大文件解析
2. embedding 批处理
3. 文档重试逻辑
4. 任务执行时的在线检索主逻辑

## 4.2 Worker 负责什么

Worker 应该承担这些 RAG 相关职责：

1. 解析文档
2. chunk 文本
3. 调 embedding 模型
4. 写入 `document_chunk`
5. 在 agent 执行前做上下文检索
6. 将检索结果注入任务上下文

## 4.3 数据库存储仍放 backend 模型层

`DocumentChunk` 当前在：

- `backend/app/models/document_chunk.py`

这个安排短期内可以保留，不必因为 RAG 重构而先改动数据库模型位置。

但要明确：

- backend 拥有 schema / migrations
- worker 可以通过数据库访问这个表
- 不应因此把 backend 里的整套 RAG 逻辑也保留下来

---

## 5. 推荐的目标代码结构

## 5.1 目标结构原则

未来应当只保留一套 RAG 核心实现，建议抽成一个真正能被 backend 和 worker 共用的模块。

**注意：当前仓库里的 `shared/` 目录虽然存在，但运行时并没有被 backend/worker 自动导入。**

原因是：

- backend 通常从 `backend/` 目录运行
- worker 通常从 `worker/` 目录运行
- 当前 `pyproject.toml` 和运行方式没有把仓库根目录作为公共 Python package 安装给两边

所以不能直接“把代码丢进 `shared/` 就算完事”。

## 5.2 推荐目标结构

建议最终收敛成：

```text
shared/
  rag/
    __init__.py
    chunker.py
    embeddings.py
    indexer.py
    retriever.py
    types.py
    parsers/
      __init__.py
      base.py
      exceptions.py
      markdown_parser.py
      pdf_parser.py
      txt_parser.py
```

同时：

- `backend/app/routers/rag.py` 只做 API 与服务编排
- `backend/app/services/` 下新增轻量 RAG orchestration service
- `worker` 调用 `shared.rag`

## 5.3 过渡期结构

如果你不想先处理 Python packaging，可以采用过渡方案：

1. **先以 `worker/rag` 为唯一实现源**
2. backend 侧不再保留 `backend/rag` 的逻辑实现
3. backend 的 RAG API 只通过任务触发 / service 调用 worker 流程

也就是说，短期过渡版可以是：

```text
backend/
  app/
    routers/rag.py
    services/rag_service.py   # orchestration only

worker/
  rag/                        # single source of truth
```

然后在第二阶段再抽到真正可复用的 `shared/rag`

---

## 6. 文件级改造建议

## 6.1 建议保留并作为基线的文件

优先保留 `worker/rag` 这一套：

- `worker/rag/chunker.py`
- `worker/rag/embeddings.py`
- `worker/rag/indexer.py`
- `worker/rag/retriever.py`
- `worker/rag/parsers/base.py`
- `worker/rag/parsers/exceptions.py`
- `worker/rag/parsers/markdown_parser.py`
- `worker/rag/parsers/pdf_parser.py`
- `worker/rag/parsers/txt_parser.py`
- `worker/rag/parsers/__init__.py`

## 6.2 建议废弃的重复实现

在完成迁移后，建议删除：

- `backend/rag/chunker.py`
- `backend/rag/embeddings.py`
- `backend/rag/indexer.py`
- `backend/rag/retriever.py`
- `backend/rag/parsers/__init__.py`

删除前提是：

- backend 的 API 已经改为调用统一 RAG 实现或统一编排服务

## 6.3 Backend 侧新增文件建议

建议新增：

- `backend/app/services/rag_service.py`

职责只做：

1. 触发索引任务
2. 提供查询封装
3. 协调文件上传与 RAG 状态更新

不要把 parser/chunker/embedding 逻辑重新塞进去。

## 6.4 Shared 侧新增文件建议

如果你准备做第二阶段抽取，建议新增：

- `shared/rag/types.py`
  - 放 chunk/result/status 类型定义
- `shared/rag/*`
  - 放统一实现

同时要调整 backend 和 worker 的依赖方式，让 `shared` 真正可 import。

---

## 7. 建议的 API 与执行流

## 7.1 文件上传后的目标链路

目标链路应当是：

```text
Frontend 上传文件
  -> Backend /projects/{id}/files/upload
  -> Backend 写入 ProjectNode + 对象存储
  -> Backend 触发“文档索引任务”
  -> Worker 执行索引
  -> Worker 解析 -> chunk -> embedding -> 写 document_chunk
  -> Backend /前端 可查询索引结果
```

### 对当前仓库的具体要求

在现有 [projects.py](F:/Programs/project_4/backend/app/routers/projects.py) 中，`upload_project_file()` 目前只完成了：

- 校验
- 写 MinIO
- 写 `ProjectNode`

重构后这里还要补一层：

- 调用 `rag_service.schedule_indexing(...)`

## 7.2 Agent 执行前的目标链路

目标链路应当是：

```text
Worker claim TaskRun
  -> 读取 Task goal
  -> 调用 retriever.retrieve(goal, project_id)
  -> 得到最相关 chunk
  -> 注入 Agent system prompt / execution context
  -> 再开始工具调用循环
```

这条链在当前仓库中还未接入。

---

## 8. 目标接口设计建议

## 8.1 Indexer 建议接口

建议统一成：

```python
class DocumentIndexer:
    async def index_document(
        self,
        project_id: str,
        file_path: str,
        content: str | None = None,
    ) -> int:
        ...
```

保留当前 `worker/rag/indexer.py` 的整体方向即可。

## 8.2 Retriever 建议接口

建议统一成：

```python
class DocumentRetriever:
    async def retrieve(
        self,
        query: str,
        project_id: str,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[dict]:
        ...
```

也基本与当前 `worker/rag/retriever.py` 一致。

## 8.3 Parser 建议接口

建议保留 `worker/rag/parsers/base.py` 的抽象基类风格：

- `parse(file_path: Path) -> dict`
- `supported_extensions() -> list[str]`

不要回退到 backend 那种把 parser 全塞到一个 `__init__.py` 里的轻量版本。

---

## 9. 三阶段迁移方案

## Phase 1：去重，但先不动 packaging

目标：

- 停止维护两套 RAG 代码
- 先把单一实现收敛到 `worker/rag`

具体动作：

1. backend 停止直接使用 `backend/rag/*`
2. 新增 `backend/app/services/rag_service.py`
3. `backend/app/routers/rag.py` 改为调用 `rag_service`
4. `projects.py` 上传文件后调用 `rag_service.schedule_indexing()`
5. 真实索引逻辑由 worker/rag 执行

这一阶段结束后：

- `backend/rag` 变成可删除候选
- RAG 单一实现先落在 worker

## Phase 2：让 RAG 成为真正共享模块

目标：

- 把单一实现从 `worker/rag` 提取到共享包

具体动作：

1. 新建 `shared/rag`
2. 把 `worker/rag` 中的基线实现迁过去
3. 修改 backend 和 worker 的依赖配置
4. 确保两边运行时都能 import `shared.rag`

这一阶段结束后：

- `worker/rag` 也可以删掉或只保留薄包装层

## Phase 3：接通完整业务闭环

目标：

- 上传即索引
- 执行前即检索
- 前端可查

具体动作：

1. 索引任务状态可观测
2. 任务执行前自动注入 RAG context
3. RAG 查询 API 不再是 stub
4. 增加测试覆盖：
   - upload -> index
   - task run -> retrieve
   - rag search -> results

---

## 10. 推荐的最小实现路径

如果你想以最小风险先推进，我建议先做下面 6 件事：

1. 以 `worker/rag` 作为唯一保留基线
2. 新增 `backend/app/services/rag_service.py`
3. 把 `backend/app/routers/rag.py` 的 stub 改成调用 service
4. 在文件上传后触发索引任务
5. 在 worker 执行任务前接入 retriever
6. 删除 `backend/rag` 重复实现

这条路径的优点是：

- 不需要第一步就处理共享包安装问题
- 能最快消除双份实现
- 能最快把 RAG 从“代码存在”变成“系统能力”

---

## 11. 风险与注意事项

## 11.1 `shared/` 当前不是现成可用的运行时共享包

这是最容易被忽略的一点。

当前不能想当然地把代码移动到根目录 `shared/` 后就假设 backend/worker 都能 import。

在真正迁移到 `shared/` 前，必须确认：

- backend 的运行方式
- worker 的运行方式
- `pyproject.toml` / 本地依赖 / `PYTHONPATH` 配置

## 11.2 `DocumentChunk.project_id` 当前是字符串

而主业务模型多为 UUID。

RAG 重构时建议至少统一一个方向：

- 要么短期全部以字符串透传
- 要么明确做 UUID -> str 的适配层

不要让这层转换散落在多个地方。

## 11.3 上传文件内容与 parser 输入目前不一致

当前 indexer 里 `content` 参数存在，但实现仍是按文件路径读取。

这意味着未来要明确：

1. 是从对象存储下载到临时文件后解析
2. 还是扩展 parser 支持直接解析内存内容

这件事在重构里必须定下来，不能继续半支持状态。

## 11.4 backend 测试与真实数据库依赖

当前 backend 部分测试依赖实际数据库连通性，这会影响 RAG API 改造后的验证方式。

因此建议在 RAG 改造时同步补：

- 更明确的 mock 策略
- 更明确的 integration / unit 边界

---

## 12. 结论

针对这个仓库，最合适的 RAG 重构方向不是：

- “全部留在 backend”
- 也不是“backend 和 worker 各做一套”

而是：

1. `backend` 做入口和控制面
2. `worker` 做执行和运行期检索
3. 核心 RAG 实现只保留一套
4. 先收敛到 `worker/rag`
5. 再在第二阶段抽成真正可运行的共享模块

一句话总结：

**先把 RAG 收敛成一套，再决定它放在哪个目录；对当前项目，执行逻辑应更靠近 worker，而不是 backend。**
