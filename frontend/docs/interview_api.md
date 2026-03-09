## 访谈助手 / Interview RAG 前端接口文档

后端 router：`backend/routers/interview/router.py`

- 统一前缀：`/interview`
- 核心能力：基于访谈文本临时构建 RAG，会话只存内存中（服务重启会丢失）。

---

## 一、创建 / 更新访谈会话

### 1. 创建或更新会话

- **方法**：`POST`
- **路径**：`/interview/session`
- **描述**：将一段或多段访谈文本切片、向量化，生成 / 更新 `session_id`，用于后续问答。

**请求体（JSON）**：

```json
{
  "session_id": "optional-session-id",
  "combined_text": "一次完整访谈的拼接文本，可选",
  "files": [
    {
      "id": "file1",
      "text": "访谈记录的第一份文本内容..."
    },
    {
      "id": "file2",
      "text": "访谈记录的第二份文本内容..."
    }
  ]
}
```

字段说明：

- `session_id`（可选）：指定会话 ID；不传则后端自动生成；传入已有的会话 ID 会覆盖原会话内容；
- `combined_text`：单段长文本可直接放此字段；
- `files`：多段文本时使用，每个元素包含 `id`（可选）和 `text`；
- `combined_text` 与 `files` 至少要有一个提供有效文本，否则会视为无效访谈文本。

**成功响应（200，CreateSessionResponse）**：

```json
{
  "success": true,
  "session_id": "a1b2c3d4-...",
  "chunks_count": 42,
  "message": "访谈会话已准备完成。"
}
```

当缺少有效文本时：

```json
{
  "success": false,
  "session_id": null,
  "chunks_count": 0,
  "message": "缺少有效的访谈文本。"
}
```

**前端使用要点**：

- 在打开“访谈助手”对话前，先调用本接口获取 `session_id`；
- 可以在会话中途重新调用本接口更新文本内容（例如补充新的访谈记录）。

---

## 二、基于访谈会话的问答

### 1. 发起一次问答

- **方法**：`POST`
- **路径**：`/interview/chat`
- **描述**：在指定访谈会话上下文下，向大模型发起问答。

**请求体（JSON，ChatRequest）**：

```json
{
  "session_id": "a1b2c3d4-...",
  "payload": null,
  "message": "本次访谈里，受访者提到过哪些科研项目？",
  "history": [
    ["上一轮用户问题", "上一轮助手回答"],
    ["更早一轮问题", "更早一轮回答"]
  ],
  "model": "qwen2.5:3b",
  "top_k": 4,
  "similarity_threshold": 0.75,
  "ollama_base_url": "http://localhost:11434"
}
```

字段说明：

- `session_id`：
  - 推荐先通过 `POST /interview/session` 创建并传入；
  - 如果不传或会话不存在，但 `payload` 中包含有效文本，后端会以该 payload 临时创建会话。
- `payload`（可选）：结构与 `POST /interview/session` 的请求体一致；用于“一步完成：构建会话 + 提问”的场景；
- `message`（必填）：当前问题；
- `history`（可选）：形如 `[[user, assistant], ...]` 的二维数组，用于多轮对话；
- `model`（可选）：Ollama 模型名，默认 `qwen2.5:3b`；
- `top_k`（可选）：从访谈片段中最多选取多少个最相似片段作为上下文，默认 4；
- `similarity_threshold`（可选）：相似度阈值（0~1），低于该值的片段会被丢弃，默认 0.75；
- `ollama_base_url`（可选）：Ollama 服务地址，默认 `http://localhost:11434`。

**成功响应（200，ChatResponse）**：

```json
{
  "success": true,
  "answer": "在本次访谈中，受访者主要提到了三个科研项目：……",
  "used_context": true,
  "session_id": "a1b2c3d4-...",
  "context_snippets": [
    "[片段1]\n……原文片段内容……",
    "[片段2]\n……原文片段内容……"
  ]
}
```

字段说明：

- `answer`：大模型生成的回答文本；
- `used_context`：是否使用了访谈片段作为上下文；
- `session_id`：实际使用的会话 ID；
- `context_snippets`：本轮回答涉及的访谈文本片段（前端可用于“高亮引用来源”）。

**错误响应示例（400）**：

```json
{
  "detail": "会话不存在且未提供有效的访谈文本。"
}
```

**前端使用要点**：

- 聊天界面每轮提问调用一次本接口；
- 建议将 `context_snippets` 以“参考来源”形式展示给用户；
- 注意处理 HTTP 400/500 错误，显示 `detail` 文本。

---

## 三、会话管理

### 1. 查询会话信息

- **方法**：`GET`
- **路径**：`/interview/session/{session_id}`

**成功响应（200，SessionInfoResponse）**：

```json
{
  "exists": true,
  "session_id": "a1b2c3d4-...",
  "chunks_count": 42,
  "created_at": 1733900000.123
}
```

当会话不存在时：

```json
{
  "exists": false,
  "session_id": "a1b2c3d4-...",
  "chunks_count": 0,
  "created_at": null
}
```

**前端使用要点**：

- 可在刷新页面后校验某个 `session_id` 是否仍然可用；
- `chunks_count` 可用于展示“已解析片段数”等统计信息。

---

### 2. 清理会话

- **方法**：`DELETE`
- **路径**：`/interview/session/{session_id}`

**成功响应（200，BasicResponse）**：

```json
{
  "success": true,
  "message": "会话 a1b2c3d4-... 已清理。"
}
```

**前端使用要点**：

- 访谈结束后可调用该接口释放内存；
- 也可提供“清理当前访谈会话”按钮给高级用户或管理员。

---

## 四、前后端集成建议

1. 推荐调用流程：
   - 用户导入 / 确认访谈文本 → 调用 `POST /interview/session` → 获得 `session_id`；
   - 前端聊天窗口使用该 `session_id` 持续调用 `POST /interview/chat`；
   - 访谈结束或会话过多时，调用 `DELETE /interview/session/{session_id}` 做清理。

2. 错误处理：
   - 成功时按 `success` 字段与 HTTP 状态码 200 处理；
   - 400/500 时读取返回体中的 `detail` 或 `message` 并展示给用户；
   - 对长时间未响应（模型推理超时）增加前端超时与“重新尝试”按钮。

3. 配置灵活性：
   - 不同环境下可通过 `model`、`ollama_base_url` 动态调整使用的模型与服务地址；
   - 如需在 UI 中支持切换模型，可将可选模型列表与本接口的 `model` 字段联动。

