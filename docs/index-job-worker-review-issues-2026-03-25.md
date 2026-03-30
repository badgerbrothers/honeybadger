# Index Job Worker 问题清单

日期：2026-03-25

范围：
- `worker/worker_indexjob.py`
- `worker/main.py`
- `worker/queueing/rabbitmq_client.py`

## 问题 1：重投递的 RUNNING 任务被直接 ack，任务可能永久卡住

严重级别：P1

涉及位置：
- `worker/worker_indexjob.py:35`
- `worker/main.py:257`
- `worker/main.py:428`

问题描述：
- `handle_index_job()` 会先调用 `claim_document_index_job_by_id()`。
- 该函数会在任务仍是 `PENDING` 时，把状态更新为 `RUNNING` 并立即 `commit`。
- 如果 worker 在 `claim` 成功后、`execute_document_index_job()` 写入终态前崩溃，RabbitMQ 会重新投递这条尚未 ack 的消息。
- 重新消费时，`claim_document_index_job_by_id()` 发现任务已经不是 `PENDING`，返回 `None`。
- `handle_index_job()` 把它当成普通重复消息直接 `return`，随后 `RabbitMQClient._handle_message()` 会对消息执行 `ack()`。
- 最终结果是：数据库中的任务仍停留在 `RUNNING`，但队列消息已经消失，且当前代码没有 stale job 恢复机制，任务会永久悬挂。

影响：
- 单次 worker 崩溃就可能造成索引任务永久卡死。
- 队列层面看起来消息已经处理完成，但业务状态并未完成。
- 后续没有补偿流程时，只能靠人工排查和修复数据库状态。

修改方法：
1. 不要把“已不是 `PENDING`”一律当成可安全忽略的重复消息。
2. 在 `handle_index_job()` 中区分以下场景：
   - 任务不存在：视为无效消息，可拒绝或丢弃。
   - 任务已是终态（如 `COMPLETED` / `FAILED`）：可视为幂等重复消息，安全 ack。
   - 任务是 `RUNNING`：不能直接 ack，应视为可能是崩溃后的重投递。
3. 对 `RUNNING` 的重投递消息，至少要保证“消息不要被静默吞掉”。可选修复方向：
   - 方案 A：抛出可重试异常，让 RabbitMQ `nack(requeue=True)`，等待后续重新投递。
   - 方案 B：引入租约/心跳/超时机制，只有确认 `RUNNING` 已超时，才允许重新 claim 或重置为 `PENDING` 后再执行。
   - 方案 C：增加后台补偿任务，定期扫描长时间停留在 `RUNNING` 的索引任务并重新入队。
4. 如果采用方案 A，必须同时解决无限重试和热循环问题，例如增加重试间隔、死信队列或超时判定。
5. 无论采用哪种方案，都需要补充测试覆盖“claim 成功后 worker 崩溃，再次收到同一消息”的场景。

建议验收标准：
- worker 在 `claim` 后崩溃，任务不会永久停留在 `RUNNING` 且无消息可继续处理。
- 重投递消息不会被错误地直接 ack。
- 恢复路径可验证、可观测，有明确日志。

## 问题 2：claim 阶段的瞬时失败在关闭 requeue 后会导致 PENDING 任务丢失

严重级别：P2

涉及位置：
- `worker/worker_indexjob.py:56`
- `worker/queueing/rabbitmq_client.py:74`
- `worker/queueing/rabbitmq_client.py:91`
- `worker/main.py:257`

问题描述：
- `worker_indexjob.py` 创建 RabbitMQ 客户端时使用了 `requeue_on_error=False`。
- 这意味着只要 `handle_index_job()` 抛出非 `ValueError` 异常，`RabbitMQClient._handle_message()` 就会执行 `message.ack()`，而不是 `nack(requeue=True)`。
- 这次 review 已确认的主路径是：`claim_document_index_job_by_id()` 在 select/commit 期间出现暂时性数据库异常，并将异常继续抛出。
- 在这个场景下，数据库中的任务仍可能保持 `PENDING`，但消息会因为 `requeue_on_error=False` 被 `ack()` 掉。
- 当前索引 worker 只消费 RabbitMQ，并不会主动轮询 `document_index_jobs` 做补发，因此这个 `PENDING` 任务后续不会再被执行。

影响：
- 短暂的数据库故障就可能直接造成 `PENDING` 索引任务丢失。
- 系统表现为“任务仍在待处理状态，但实际上再也不会被消费”。
- 这类问题不容易从业务状态直接看出来，因为消息已经被正常 ack。

修改方法：
1. 恢复索引 worker 的瞬时错误重试能力，不要对所有非校验类异常直接 ack。
2. 优先方案：
   - 将 `worker/worker_indexjob.py` 中的 `requeue_on_error` 改回 `True`。
   - 保持 `ValueError` 这类明确不可重试的错误继续 `reject(requeue=False)`。
3. 如果担心无限重试，需要配套增加以下机制之一：
   - 基于消息头或数据库字段记录重试次数，超过阈值后标记 `FAILED`。
   - 配置 RabbitMQ 死信队列，让多次失败的消息进入死信而不是永久重试。
   - 对异常做可重试/不可重试分类，避免把确定性失败做成无限重试。
4. 扩展风险说明：
   - 其他执行阶段异常是否也会因为当前 ack 策略导致任务丢失，属于合理风险推演，但不属于这次 review 已明确证明的主问题。
   - 如果后续要扩大修复范围，建议单独补充对 `execute_document_index_job()` 期间异常边界的验证。
5. 补充测试：
   - `claim_document_index_job_by_id()` 抛出临时异常时，消息应 `nack(requeue=True)`。
   - 明确不可重试的参数错误仍然应被丢弃而不是重试。

建议验收标准：
- `claim_document_index_job_by_id()` 的暂时性异常不会让 `PENDING` 任务无声丢失。
- 失败消息具备明确的重试或死信归宿。
- 任务最终状态与队列 ack/nack 语义保持一致。

## 修改顺序建议

1. 先确定索引任务的恢复策略：采用“重试驱动恢复”还是“补偿扫描恢复”，或者两者结合。
2. 再调整 `handle_index_job()` 对 `RUNNING` 状态的处理，避免误 ack 重投递消息。
3. 最后恢复瞬时异常的 requeue 策略，并补齐对应测试。

## 备注

这份清单只记录问题和建议修改方案，当前未修改任何代码。
