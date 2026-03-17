# RAG 系统技术指南

> 文档版本：v1.0
> 更新日期：2026-03-16
> 适用范围：Badgers MVP RAG 模块

## 1. 概述

RAG (Retrieval-Augmented Generation) 系统为 Badgers 平台提供项目级知识检索能力，使 AI Agent 能够基于项目文档生成更准确的回答。

### 核心功能
- 文档自动索引（TXT/Markdown/PDF）
- 向量相似度检索
- 异步任务调度
- 项目上下文注入

### 架构位置
```
Backend (控制平面)
  ├── API 路由 (routers/rag.py)
  ├── 服务层 (services/rag_service.py)
  └── RAG 库 (rag/)

Worker (执行平面)
  ├── 索引任务执行 (main.py)
  ├── 上下文检索 (main.py:retrieve_project_context)
  └── RAG 库 (rag/)
```

## 2. 模块结构

### Backend RAG (`backend/rag/`)

```
backend/rag/
├── embeddings.py      # OpenAI 嵌入服务
├── chunker.py         # 文档分块（tiktoken）
├── indexer.py         # 文档索引管道
├── retriever.py       # 相似度检索
└── parsers/
    └── __init__.py    # TXT/Markdown/PDF 解析器
```

### Worker RAG (`worker/rag/`)

```
worker/rag/
├── embeddings.py      # 同 backend 实现
├── chunker.py         # 同 backend 实现
├── indexer.py         # 同 backend 实现
├── retriever.py       # 同 backend 实现
└── parsers/           # 更详细的解析器实现
    ├── base.py
    ├── exceptions.py
    ├── markdown_parser.py
    ├── txt_parser.py
    └── pdf_parser.py
```

**注意**：当前存在代码重复，未来应统一为单一实现。

## 3. 核心组件

### 3.1 EmbeddingService

**位置**：`backend/rag/embeddings.py`

**功能**：使用 OpenAI API 生成文本向量嵌入

```python
from rag.embeddings import EmbeddingService

service = EmbeddingService(api_key="sk-...", model="text-embedding-3-small")

# 单个文本
embedding = await service.generate_embedding("Hello world")  # List[float], 1536维

# 批量处理（最多2048条）
embeddings = await service.generate_embeddings_batch(["text1", "text2"])
```

**配置**：
- 模型：`text-embedding-3-small` (1536维)
- API密钥：环境变量 `OPENAI_API_KEY`
- 批量限制：2048 条/批

### 3.2 Chunker

**位置**：`backend/rag/chunker.py`

**功能**：将长文本分割为固定大小的块，保持上下文连续性

```python
from rag.chunker import chunk_text

chunks = chunk_text(
    text="长文本内容...",
    chunk_size=512,    # tokens
    overlap=50         # tokens
)

# 返回格式
[
    {
        "content": "块文本内容",
        "chunk_index": 0,
        "start_pos": 0,
        "end_pos": 512,
        "token_count": 512
    },
    ...
]
```

**参数说明**：
- `chunk_size`：每块的 token 数量（默认512）
- `overlap`：块之间的重叠 token 数（默认50）
- 使用 tiktoken `cl100k_base` 编码

### 3.3 DocumentIndexer

**位置**：`backend/rag/indexer.py`

**功能**：完整的文档索引管道

```python
from rag.indexer import DocumentIndexer
from rag.embeddings import EmbeddingService

indexer = DocumentIndexer(
    embedding_service=EmbeddingService(api_key, model),
    db_session=session
)

# 索引文档
chunk_count = await indexer.index_document(
    project_id="uuid-string",
    file_path="/path/to/file.pdf"
)
```

**处理流程**：
1. 解析文档 → 提取文本
2. 分块 → 512 tokens/块，50 tokens 重叠
3. 生成嵌入 → 批量调用 OpenAI API
4. 存储 → 写入 `DocumentChunk` 表

**支持格式**：`.txt`, `.md`, `.markdown`, `.pdf`

### 3.4 DocumentRetriever

**位置**：`backend/rag/retriever.py`

**功能**：基于向量相似度检索相关文档块

```python
from rag.retriever import DocumentRetriever

retriever = DocumentRetriever(embedding_service, db_session)

chunks = await retriever.retrieve(
    query="用户查询文本",
    project_id="uuid-string",
    top_k=5,           # 返回前5个结果
    threshold=0.7      # 相似度阈值
)

# 返回格式
[
    {
        "id": 123,
        "content": "匹配的文本内容",
        "file_path": "docs/readme.md",
        "chunk_index": 2,
        "similarity": 0.85,
        "metadata": {...}
    },
    ...
]
```

**相似度计算**：
- 使用 pgvector 的余弦相似度
- 公式：`similarity = 1 - cosine_distance(query_embedding, chunk_embedding)`
- 只返回 `similarity >= threshold` 的结果

## 4. API 接口

### 4.1 创建索引任务

**端点**：`POST /api/projects/{project_id}/documents/index`

**请求体**：
```json
{
  "node_id": "uuid-of-project-node"
}
```

**响应**：
```json
{
  "job_id": "uuid",
  "status": "pending",
  "project_id": "uuid",
  "node_id": "uuid"
}
```

**说明**：为已上传的项目文件创建索引任务，Worker 会自动执行。

### 4.2 搜索文档

**端点**：`POST /api/projects/{project_id}/search`

**请求体**：
```json
{
  "query": "搜索关键词或问题",
  "top_k": 5,
  "threshold": 0.7
}
```

**响应**：
```json
{
  "query": "搜索关键词或问题",
  "chunks": [
    {
      "id": 123,
      "content": "匹配的文本内容",
      "file_path": "docs/readme.md",
      "chunk_index": 2,
      "similarity": 0.85,
      "metadata": {}
    }
  ]
}
```

### 4.3 列出索引块

**端点**：`GET /api/projects/{project_id}/chunks`

**响应**：
```json
[
  {
    "id": 123,
    "file_path": "docs/readme.md",
    "chunk_index": 0,
    "token_count": 512
  }
]
```

### 4.4 删除索引块

**端点**：`DELETE /api/projects/{project_id}/chunks/{chunk_id}`

**响应**：`204 No Content`

## 5. 数据模型

### 5.1 DocumentChunk

**表名**：`document_chunks`

**字段**：
```python
id: int                    # 主键
project_id: str            # 项目ID（注意：类型为str，其他模型用UUID）
file_path: str             # 文件路径
chunk_index: int           # 块索引（从0开始）
content: str               # 文本内容
embedding: Vector(1536)    # 向量嵌入（pgvector类型）
token_count: int           # token数量
chunk_metadata: JSON       # 元数据（start_pos, end_pos等）
created_at: datetime       # 创建时间
```

### 5.2 DocumentIndexJob

**表名**：`document_index_jobs`

**字段**：
```python
id: UUID                   # 主键
project_id: UUID           # 项目ID
project_node_id: UUID      # 文件节点ID
storage_path: str          # MinIO存储路径
file_name: str             # 文件名
status: Enum               # PENDING/RUNNING/COMPLETED/FAILED
started_at: datetime       # 开始时间
completed_at: datetime     # 完成时间
chunk_count: int           # 索引的块数量
error_message: str         # 错误信息
created_at: datetime       # 创建时间
```

**状态流转**：
```
PENDING → RUNNING → COMPLETED
                 ↘ FAILED
```

## 6. 完整使用流程

### 6.1 文档索引流程

```
1. 用户上传文件
   ↓
2. Backend创建ProjectNode
   ↓
3. 调用 POST /api/projects/{id}/documents/index
   ↓
4. Backend创建DocumentIndexJob（状态：PENDING）
   ↓
5. Worker轮询到任务
   ↓
6. Worker执行索引：
   - 从MinIO下载文件
   - 解析文档提取文本
   - 分块（512 tokens，50重叠）
   - 生成嵌入（批量调用OpenAI）
   - 存储到DocumentChunk表
   ↓
7. 更新任务状态为COMPLETED
```

### 6.2 任务执行时的上下文检索

```python
# worker/main.py:retrieve_project_context()

async def retrieve_project_context(task, task_run, session):
    """为任务检索相关项目文档"""

    # 1. 使用任务目标作为查询
    query = task.goal

    # 2. 检索top 5相似块（阈值0.55）
    chunks = await retriever.retrieve(
        query=query,
        project_id=task.project_id,
        top_k=5,
        threshold=0.55
    )

    # 3. 格式化为上下文字符串
    context = "Relevant project context:\n"
    for chunk in chunks:
        context += f"[{chunk['file_path']}#{chunk['chunk_index']}] {chunk['content']}\n\n"

    # 4. 注入到Agent系统提示
    return context
```

### 6.3 Agent使用RAG上下文

```python
# worker/main.py:execute_task_run()

# 检索项目上下文
rag_context = await retrieve_project_context(task, task_run, session)

# 合并技能提示和RAG上下文
system_prompt = build_system_prompt(
    skill_prompt=skill.system_prompt if skill else None,
    rag_context=rag_context
)

# 创建Agent并执行
agent = Agent(...)
result = await agent.run(goal=task.goal, system_prompt=system_prompt)
```

## 7. 配置说明

### 7.1 环境变量

**Backend 配置**：
```bash
# OpenAI API（必需）
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，默认官方API

# 嵌入模型
EMBEDDING_MODEL=text-embedding-3-small  # 默认值

# 数据库（必需）
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

**Worker 配置**：
```bash
# 同Backend配置
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# MinIO/S3（必需）
S3_ENDPOINT=minio:9000
S3_ACCESS_KEY=badgers
S3_SECRET_KEY=badgers_dev_password
S3_BUCKET=badgers-artifacts
S3_SECURE=false
```

### 7.2 数据库扩展

**启用 pgvector**：
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**迁移文件**：`backend/alembic/versions/001_pgvector.py`

### 7.3 分块参数调优

**修改位置**：`backend/rag/indexer.py:_chunk_document()`

```python
# 默认配置
chunk_size = 512   # tokens/块
overlap = 50       # tokens重叠

# 调优建议：
# - 技术文档：chunk_size=1024, overlap=100
# - 对话记录：chunk_size=256, overlap=25
# - 长篇文章：chunk_size=768, overlap=75
```

### 7.4 检索参数调优

**修改位置**：`worker/main.py:retrieve_project_context()`

```python
# 默认配置
top_k = 5          # 返回前5个结果
threshold = 0.55   # 相似度阈值

# 调优建议：
# - 提高精度：threshold=0.7, top_k=3
# - 提高召回：threshold=0.4, top_k=10
# - 平衡模式：threshold=0.55, top_k=5（当前默认）
```

## 8. 故障排查

### 8.1 索引任务失败

**症状**：`DocumentIndexJob` 状态为 `FAILED`

**排查步骤**：
1. 查看 `error_message` 字段
2. 检查 Worker 日志：`docker logs badgers-worker`
3. 常见原因：
   - OpenAI API 密钥无效或额度不足
   - 文件格式不支持或损坏
   - MinIO 连接失败

**解决方案**：
```bash
# 检查API密钥
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 检查MinIO连接
mc alias set myminio http://localhost:9000 $S3_ACCESS_KEY $S3_SECRET_KEY

# 重新调度任务
POST /api/projects/{project_id}/documents/index
{
  "node_id": "failed-node-uuid"
}
```

### 8.2 检索结果为空

**症状**：搜索返回空数组

**排查步骤**：
1. 确认文档已索引：`GET /api/projects/{project_id}/chunks`
2. 检查相似度阈值是否过高
3. 验证查询文本是否与文档内容相关

**解决方案**：
```python
# 降低阈值测试
chunks = await retriever.retrieve(
    query="test query",
    project_id=project_id,
    top_k=10,
    threshold=0.3  # 降低阈值
)

# 检查原始相似度分数
for chunk in chunks:
    print(f"Similarity: {chunk['similarity']}")
```

### 8.3 嵌入生成速度慢

**症状**：索引大文件耗时过长

**原因**：批量大小不足，API 调用次数过多

**优化方案**：
```python
# backend/rag/indexer.py:_generate_embeddings()

# 当前批量大小
batch_size = 2048  # OpenAI限制

# 优化：并发处理多个批次
import asyncio

async def _generate_embeddings_concurrent(self, chunks):
    batch_size = 2048
    batches = [chunks[i:i+batch_size] for i in range(0, len(chunks), batch_size)]

    tasks = [
        self.embedding_service.generate_embeddings_batch([c["content"] for c in batch])
        for batch in batches
    ]

    results = await asyncio.gather(*tasks)
    return [emb for batch_result in results for emb in batch_result]
```

### 8.4 pgvector 性能问题

**症状**：检索查询耗时超过 1 秒

**解决方案**：创建向量索引

```sql
-- 创建 IVFFlat 索引（适合中等规模数据）
CREATE INDEX document_chunks_embedding_idx
ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 或创建 HNSW 索引（适合大规模数据，需 pgvector 0.5.0+）
CREATE INDEX document_chunks_embedding_hnsw_idx
ON document_chunks
USING hnsw (embedding vector_cosine_ops);
```

## 9. 性能优化建议

### 9.1 批量索引优化

**当前实现**：逐个文件索引

**优化方案**：批量调度多个索引任务

```python
# 批量创建索引任务
async def batch_schedule_indexing(project_id: UUID, node_ids: List[UUID], db: AsyncSession):
    jobs = []
    for node_id in node_ids:
        job = await rag_service.requeue_node(project_id, node_id, db)
        if job:
            jobs.append(job)
    return jobs
```

### 9.2 缓存嵌入结果

**优化方案**：缓存查询嵌入，避免重复计算

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
async def cached_generate_embedding(text: str) -> List[float]:
    return await embedding_service.generate_embedding(text)
```

### 9.3 增量索引

**当前实现**：文件更新需重新索引全部内容

**优化方案**：
1. 检测文件变更（hash 比对）
2. 只重新索引变更的块
3. 删除旧块，插入新块

## 10. 已知问题与改进方向

### 10.1 代码重复

**问题**：Backend 和 Worker 各有一套完整的 RAG 实现

**影响**：维护成本高，容易出现不一致

**改进方案**：
- 将 RAG 库提取到 `shared/rag/`
- Backend 和 Worker 共享同一实现
- 通过依赖注入适配不同环境

### 10.2 类型不一致

**问题**：`DocumentChunk.project_id` 是 `str`，其他模型用 `UUID`

**影响**：类型转换繁琐，容易出错

**改进方案**：
```python
# 迁移脚本
ALTER TABLE document_chunks
ALTER COLUMN project_id TYPE UUID USING project_id::UUID;
```

### 10.3 文件上传未自动索引

**问题**：上传文件后需手动调用索引 API

**影响**：用户体验差，容易遗漏

**改进方案**：
```python
# backend/app/routers/projects.py:upload_project_file()

# 上传成功后自动调度索引
await rag_service.schedule_indexing(
    project_id=project_id,
    project_node_id=node.id,
    storage_path=storage_path,
    file_name=file.filename,
    db=db
)
```

### 10.4 缺少前端集成

**问题**：无 UI 展示索引状态和搜索功能

**改进方案**：
- 项目详情页显示索引任务列表
- 添加文档搜索界面
- 实时显示索引进度

## 11. 相关文档

- [PRD - RAG 系统需求](../../.claude/PRD.md#rag-system)
- [RAG 重构计划](../rag-refactor-plan.md)
- [系统架构文档](../current-system-architecture.md)
- [测试指南](../testing-guidelines.md)

## 12. 快速参考

### 常用命令

```bash
# 查看索引任务
psql -c "SELECT id, status, file_name, chunk_count FROM document_index_jobs ORDER BY created_at DESC LIMIT 10;"

# 查看索引块统计
psql -c "SELECT project_id, COUNT(*) as chunk_count, SUM(token_count) as total_tokens FROM document_chunks GROUP BY project_id;"

# 手动触发索引
curl -X POST http://localhost:8000/api/projects/{project_id}/documents/index \
  -H "Content-Type: application/json" \
  -d '{"node_id": "uuid"}'

# 搜索测试
curl -X POST http://localhost:8000/api/projects/{project_id}/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 5, "threshold": 0.7}'
```

### 关键指标

| 指标 | 正常范围 | 说明 |
|------|---------|------|
| 索引速度 | 100-500 chunks/min | 取决于文档大小和API速度 |
| 检索延迟 | < 500ms | 包含嵌入生成和向量搜索 |
| 相似度阈值 | 0.5-0.8 | 低于0.5可能返回不相关结果 |
| 块大小 | 256-1024 tokens | 过小损失上下文，过大降低精度 |

---

**维护者**：Badgers 开发团队
**最后更新**：2026-03-16
