# Badgers TaskRun / Retry 职责划分与重试方案

本文档基于当前代码基线与 2026-03-24 的设计讨论整理，目标是统一 `Task`、`TaskRun`、RabbitMQ 消息消费、失败处理与 retry 归属。

## 1. 文档目的

- 明确 `TaskRun` 在系统中的业务语义
- 统一 `task-service` 与 `worker` 对 retry 的职责划分
- 终止“旧 `TaskRun` 被 RabbitMQ requeue 后重复执行”的冲突语义
- 为后续代码改造提供单一设计基线

## 2. 需求结论

基于当前讨论，最终需求收敛为以下几点：

1. `TaskRun` 表示一次独立执行尝试
2. 一个 `Task` 可以有多个 `TaskRun`
3. 同一个 `TaskRun` 不能因为 RabbitMQ `requeue` 被反复执行
4. 业务级 retry 必须创建新的 `TaskRun`
5. retry 是否发生，由上游 `task-service` 根据失败信息做策略判断
6. `worker` 负责执行一个既定的 `TaskRun`，不负责业务级 retry 决策
7. 当前阶段不引入 worker 内部“小重试”机制，先保证状态机与职责边界正确

## 3. Project Overview

- 应用类型：单仓多服务 AI 执行系统
- 相关主模块：
  - `services/task-service/`：任务、运行、事件、队列发布
  - `worker/`：TaskRun 执行、sandbox 生命周期、agent/tool 调用
  - `RabbitMQ`：任务消息传递
  - `PostgreSQL`：`Task`、`TaskRun`、`SandboxSession` 等持久化
- 当前运行链路：
  - `task-service` 创建 `TaskRun`
  - 发布 `task_run_id` 到 `task-runs`
  - `worker-taskrun` 消费并执行
  - `worker` 回传事件到 `task-service`

## 4. Current State

当前代码已经具备以下事实：

- `Task` 与 `TaskRun` 是一对多关系
- `Task.current_run_id` 只表示当前活动 run
- `retry` API 会创建新的 `TaskRun`
- `worker` 会为每个 run 创建一个 `SandboxSession`
- `worker` 失败时会把当前 `TaskRun` 标记为 `FAILED`
- `worker` 还会向 `task-service` 上报 `run_failed` 事件

当前代码同时存在以下问题：

1. 生产者和消费者对 retry 语义不一致
   - 上游已经把 retry 设计成“创建新 `TaskRun`”
   - 下游 RabbitMQ 消费失败时却会 `nack(requeue=True)`，等价于“重跑旧 `TaskRun`”

2. 旧 run 可能被重复执行
   - 同一个 `task_run_id` 若被重新投递，旧逻辑会再次进入执行链
   - 这与“`TaskRun` 是一次尝试”的业务语义冲突

3. `retry` 与旧 run 停止逻辑未完全对齐
   - 上游当前有显式 retry 入口
   - 但旧 run 的取消、终止、拒绝再次执行等控制仍需加强

4. 失败信息虽然会回传，但还没有形成“上游策略判断并自动 retry”的完整闭环

## 5. Core Principles

本方案以以下原则为准：

### 5.1 `TaskRun` 是一次性执行记录

- 一个 `TaskRun` 只允许有一次真实执行
- 执行完成后进入终态：
  - `COMPLETED`
  - `FAILED`
  - `CANCELLED`
- 终态后的同一 `TaskRun` 不能再次进入执行

### 5.2 业务级 retry 归 `task-service`

- 是否 retry 是业务/调度决策，不是执行细节
- `task-service` 应根据失败信息判断：
  - 是否可重试
  - 是否已超过最大重试次数
  - 是否需要延迟或退避
  - 是否属于永久失败

### 5.3 `worker` 只执行，不调度业务 retry

- `worker` 的职责是执行一个既定的 `TaskRun`
- `worker` 不应通过 requeue 让旧 `TaskRun` 再次执行
- `worker` 失败后应明确结束当前 run，并把失败信息回传给 `task-service`

### 5.4 RabbitMQ 不承担业务 retry 语义

- RabbitMQ 可以承担消息传递
- 但不应通过 `requeue` 来表达“再来一次新的执行尝试”
- “新的尝试”必须是新的 `TaskRun`

## 6. 目标职责划分

## 6.1 `task-service` 职责

- 创建 `Task`
- 创建 `TaskRun`
- 发布 `task_run_id` 到 `task-runs`
- 接收并持久化 worker 事件
- 基于失败信息判断是否创建新的 retry run
- 管理 `Task.current_run_id`
- 提供手动 retry、取消、查询历史 run 的 API

## 6.2 `worker` 职责

- 消费 `task_run_id`
- claim 指定 `TaskRun`
- 校验 run 状态是否合法
- 创建和销毁 sandbox
- 执行 agent / tools
- 将当前 run 落为终态
- 回传结构化事件与结构化失败信息

## 6.3 RabbitMQ 职责

- 传递待执行的 `task_run_id`
- 不负责业务级 retry
- 不应成为“旧 `TaskRun` 重跑”的机制

## 7. Target Flow

## 7.1 正常执行

```text
task-service
  -> create TaskRun(R1, status=PENDING)
  -> publish { task_run_id: R1 }

worker
  -> consume R1
  -> claim R1: PENDING -> RUNNING
  -> create sandbox
  -> execute
  -> mark R1 COMPLETED
  -> destroy sandbox
  -> ack message
```

## 7.2 执行失败但不 retry

```text
task-service
  -> create TaskRun(R1)
  -> publish R1

worker
  -> consume R1
  -> claim R1
  -> execute failed
  -> mark R1 FAILED
  -> report structured failure to task-service
  -> destroy sandbox
  -> ack message

task-service
  -> persist failed info
  -> policy result: no retry
```

## 7.3 执行失败并触发 retry

```text
task-service
  -> create TaskRun(R1)
  -> publish R1

worker
  -> execute R1 failed
  -> mark R1 FAILED
  -> report structured failure
  -> ack message

task-service
  -> evaluate failure policy
  -> create TaskRun(R2, status=PENDING)
  -> task.current_run_id = R2
  -> publish { task_run_id: R2 }
```

关键点：

- `R1` 不会 requeue 后再次执行
- `R2` 是一条新的业务尝试
- run 历史清晰可审计

## 8. 明确禁止的行为

以下行为与本方案冲突，应明确禁止：

1. 使用 RabbitMQ `requeue` 表示业务 retry
2. 让同一个 `task_run_id` 多次进入真实执行
3. 在 `worker` 内部创建新的业务级 `TaskRun`
4. 让 `retry` 复活旧的失败 run
5. 在旧 run 尚未被终止或拒绝继续执行时，默默覆盖 `Task.current_run_id`

## 9. 失败信息要求

既然 retry 决策归 `task-service`，则 `worker` 回传的失败信息不能只是一段随意字符串，而应尽量结构化。

建议最小字段：

- `type`: `run_failed`
- `error_message`
- `error_category`
  - `model_api`
  - `sandbox`
  - `tool`
  - `validation`
  - `internal`
- `retryable_hint`
  - `true`
  - `false`
- `failed_step`
  - `claim`
  - `sandbox_create`
  - `agent_run`
  - `tool_execute`
  - `artifact_upload`
- `timestamp`

说明：

- `retryable_hint` 只是 worker 提示，不是最终决策
- 最终是否 retry 由 `task-service` 策略层决定

## 10. 状态机约束

## 10.1 `TaskRun.status`

允许状态：

- `PENDING`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

允许迁移：

- `PENDING -> RUNNING`
- `RUNNING -> COMPLETED`
- `RUNNING -> FAILED`
- `PENDING -> CANCELLED`
- `RUNNING -> CANCELLED`

禁止迁移：

- `FAILED -> RUNNING`
- `COMPLETED -> RUNNING`
- `CANCELLED -> RUNNING`
- 任意终态 -> `PENDING`

## 10.2 `Task.current_run_id`

约束如下：

- 指向当前活跃 run
- run 进入终态后应被清空，或切换为新创建的 retry run
- 不应长期指向已终态但不再执行的 run

## 11. 当前阶段的具体设计决定

为了降低复杂度，当前阶段明确采用以下决定：

1. `TaskRun` 继续由上游 `task-service` 创建
2. `worker` 不负责创建新的 retry run
3. RabbitMQ consumer 关闭业务异常下的 `requeue`
4. 当前阶段不加 worker 内部“小重试”
5. 自动 retry 策略放在 `task-service`
6. `worker` 失败后必须把失败信息回传给 `task-service`
7. `task-service` 根据失败信息决定是否创建下一个 run

## 12. 代码改造方向

## 12.1 `task-service` 需要补的内容

### A. 失败策略层

新增一层 retry policy 逻辑，负责：

- 读取 run 的失败信息
- 读取该 task 的历史 run 数量与失败历史
- 判断是否自动 retry
- 创建新的 `TaskRun`
- 重新发布到 `task-runs`

可落点：

- `services/task-service/app/services/`

建议新增：

- `task_retry_service.py`
- `task_run_policy.py`

### B. run_failed 事件的消费闭环

当前 `/api/runs/{run_id}/events` 主要负责记日志与广播，后续应扩展为：

- 持久化结构化失败信息
- 在 `run_failed` 事件到达时触发 retry policy 评估

### C. retry 前的活跃 run 防护

对手动 retry 或自动 retry，都应保证：

- 若旧 run 仍是 `PENDING/RUNNING`
  - 要么先取消旧 run
  - 要么拒绝创建新 run

不能只覆盖 `task.current_run_id`。

## 12.2 `worker` 需要补的内容

### A. 不再把业务异常作为 requeue 条件

当前消费语义应调整为：

- payload 非法：`reject(requeue=False)`
- run 不存在或状态不合法：直接跳过并 `ack`
- 业务执行失败：写 `FAILED`，回传失败信息，然后 `ack`

目标是：

- 旧消息不会因为业务失败而再次驱动同一个 run 执行

### B. 执行前必须做状态校验

`worker` 在收到 `task_run_id` 后必须：

1. 查询 run
2. 仅 claim `PENDING`
3. 仅执行 `RUNNING`
4. 若 run 已是终态，则直接跳过

### C. sandbox 幂等保护

`worker` 在创建 sandbox 前应检查：

- 该 run 是否已存在 `SandboxSession`
- 是否已终态

避免重复创建 sandbox。

## 13. 非目标

当前文档明确不做以下事项：

1. 不把 `TaskRun` 创建权迁移到 worker
2. 不把队列 payload 从 `task_run_id` 改为 `task_id`
3. 不在当前阶段引入 worker 内部指数退避小重试
4. 不用 RabbitMQ 原生 `requeue` 实现业务级 retry

## 14. 实施顺序建议

1. 先关闭 worker 业务异常下的 `requeue`
2. 先保证 worker 对非 `PENDING/RUNNING` run 不执行
3. 扩展 `run_failed` 失败信息结构
4. 在 `task-service` 引入 retry policy
5. 接通自动 retry 创建新 `TaskRun` 的闭环
6. 最后再考虑是否需要小重试或延迟重试

## 15. 一句话结论

最终基线应为：

`TaskRun` 是一次执行尝试；失败后旧 run 结束，不通过 RabbitMQ requeue 重跑；是否 retry 由 `task-service` 基于失败信息判断，并通过创建新的 `TaskRun` 发起下一次尝试。
