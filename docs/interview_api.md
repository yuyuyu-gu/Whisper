# 访谈助手 / RAG 临时问答 API 文档

> 基于 `TemporaryRAGChatService` 的推荐 REST 接口设计，用于对接“访谈问答助手”。

---

## 一、总体说明

- **功能定位**：基于单次或少量访谈文本构建**临时知识库**，支持在访谈上下文基础上的问答。
- **实现基础**：
  - 向量化：`sentence-transformers`（默认 `paraphrase-multilingual-MiniLM-L12-v2`）
  - 检索：内存中余弦相似度匹配
  - 回答生成：通过 Ollama 调用大模型（默认 `qwen2.5:3b`，本地 `http://localhost:11434/api/chat`）
- **会话状态**：
  - 通过 `session_id` 标识一次访谈会话；
  - 会话只保存在内存中，服务重启后会失效。

推荐统一前缀：`/interview`

---

## 二、创建 / 更新访谈会话（构建临时 RAG）

### 1. 创建 / 更新临时会话

- **方法**：`POST`
- **路径**：`/interview/session`
- **描述**：将访谈文本（或多段文本）切片、向量化，并缓存在内存中，生成一个 `session_id`，供后续问答使用。

- **请求体（JSON）**：

```json
{
  "session_id": "optional-session-id",      // 可选，传入则尝试复用；不传则自动生成
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

- 字段说明：
  - `session_id`（可选）：指定会话 ID；若不传则后端生成一个新的 UUID。
  - `combined_text`：当只有一整段记录时可以直接放这里。
  - `files`：当有多份记录（多段访谈、多个文件）时，每份放在 `files[i].text` 中。
  - `combined_text` 和 `files` 至少要有一者非空，否则返回失败。

- **成功响应示例**：

```json
{
  "success": true,
  "session_id": "a1b2c3d4-...",
  "chunks_count": 42,
  "message": "访谈会话已准备完成。"
}
```

- **失败响应示例**：

```json
{
  "success": false,
  "message": "缺少有效的访谈文本。"
}
```

> 内部对应：`TemporaryRAGChatService.ensure_session(payload)`。
> 会将文本拆分为片段（默认 `chunk_size=420`，`chunk_overlap=60`），并计算向量。

---

## 三、基于会话的问答（访谈助手）

### 1. 发起一次问答

- **方法**：`POST`
- **路径**：`/interview/chat`
- **描述**：在指定访谈会话上下文下，向 Ollama 发起一次问答；如果会话不存在则可随请求携带 payload 自动创建。

- **请求体（JSON）**：

```json
{
  "session_id": "a1b2c3d4-...",        // 推荐：先通过 /interview/session 获取
  "payload": {
    "session_id": "a1b2c3d4-...",
    "combined_text": "",
    "files": []
  },
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

- 字段说明：
  - `session_id`：
    - 推荐先用 `/interview/session` 创建并传入；
    - 如果不传或会话不存在，且 `payload` 中带有文本，后端会尝试基于 payload 临时创建一个会话。
  - `payload`（可选）：
    - 结构同 `/interview/session` 的请求体；
    - 用于“一步完成：构建会话 + 提问”的简化场景。
  - `message`：本轮用户提问内容（必填）。
  - `history`（可选）：
    - 形如 `[[user, assistant], ...]` 的二维数组，用于保留多轮对话上下文。
  - `model`（可选）：Ollama 模型名，默认 `qwen2.5:3b`。
  - `top_k`（可选）：从访谈片段中最多选取多少个最相似片段作为上下文，默认 4。
  - `similarity_threshold`（可选）：余弦相似度阈值，低于该值的片段会被丢弃，默认 0.75。
  - `ollama_base_url`（可选）：Ollama 服务地址，默认 `http://localhost:11434`。

- **成功响应示例**：

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

- 字段说明：
  - `answer`：大模型生成的回复文本。
  - `used_context`：是否成功从访谈文本中检索到相关片段（`true` 表示回答主要基于访谈内容）。
  - `context_snippets`：本次回答所使用的访谈片段（友好格式，方便前端做“引用高亮”）。

- **失败响应示例**：

```json
{
  "success": false,
  "message": "会话不存在且未提供有效的访谈文本。",
  "session_id": null
}
```

> 内部对应：`TemporaryRAGChatService.generate_reply(...)`。
> 流程：构建 / 复用 session → 检索相似片段 → 构造 system prompt + history + message → 调用 Ollama `/api/chat`。

---

## 四、会话管理（可选）

### 1. 查询会话信息

- **方法**：`GET`
- **路径**：`/interview/session/{session_id}`

- **响应示例**：

```json
{
  "exists": true,
  "session_id": "a1b2c3d4-...",
  "chunks_count": 42,
  "created_at": 1733900000.123
}
```

- 当会话不存在时：

```json
{
  "exists": false,
  "session_id": "a1b2c3d4-...",
  "chunks_count": 0
}
```

> 内部可直接从 `_sessions` 字典中读取会话元数据。

---

### 2. 清理会话

- **方法**：`DELETE`
- **路径**：`/interview/session/{session_id}`

- **响应示例**：

```json
{
  "success": true,
  "message": "会话 a1b2c3d4-... 已清理。"
}
```

> 对应 `TemporaryRAGChatService.clear_session(session_id)`，用于在访谈结束后释放内存。

---

## 五、前后端对接建议

1. **推荐调用顺序**：
   - 上传/整理访谈文本 → 调用 `POST /interview/session` → 拿到 `session_id`；
   - 前端聊天界面反复调用 `POST /interview/chat` 进行问答；
   - 访谈结束或会话过多时，可调用 `DELETE /interview/session/{session_id}` 释放内存。

2. **错误处理**：
   - 建议前端统一根据 `success` 字段判断是否成功，失败时展示 `message`；
   - 长时间未响应（Ollama 推理超时）时，应在前端增加超时提示。

3. **模型与参数配置**：
   - 若部署环境中 Ollama 模型名或地址不同，可通过 `model`、`ollama_base_url` 字段灵活覆盖默认配置。

