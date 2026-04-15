对 Habit Tracker 项目执行完整验证。

按顺序执行以下命令并汇报结果：

## 1. 后端 Lint 检查

```bash
cd backend && uv run ruff check .
```

**预期结果：** 输出 `"All checks passed!"`，或者无输出（表示干净）

## 2. 后端测试

```bash
cd backend && uv run pytest -v
```

**预期结果：** 所有测试通过，执行时间小于 5 秒

## 3. 带覆盖率的后端测试

```bash
cd backend && uv run pytest --cov=app --cov-report=term-missing
```

**预期结果：** 覆盖率 >= 80%（在 `pyproject.toml` 中配置）

## 4. 前端构建

```bash
cd frontend && npm run build
```

**预期结果：** 构建成功完成，并输出到 `dist/` 目录

## 5. 本地服务验证（可选）

如果后端尚未运行，先启动它：

```bash
cd backend && uv run uvicorn app.main:app --port 8000 &
```

等待 2 秒后执行测试：

```bash
# 测试 habits 接口
curl -s http://localhost:8000/api/habits | head -c 200

# 检查 API 文档
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8000/docs
```

**预期结果：** `habits` 接口返回 JSON，文档地址返回 HTTP 200

如果是你启动的服务，测试后将其停止：

```bash
# Windows
taskkill /F /IM uvicorn.exe 2>nul || true

# Linux/Mac
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
```

## 6. 汇总报告

完成所有验证后，输出一份摘要报告，内容包括：

- Lint 状态
- 测试通过 / 失败情况
- 覆盖率百分比
- 前端构建状态
- 遇到的错误或警告
- 总体健康评估（PASS / FAIL）

**请用清晰的分节与状态标记格式化报告**
