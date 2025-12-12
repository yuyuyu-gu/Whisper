# 任务与结果 / Task API 文档

后端 router：`backend/routers/task/router.py`

> 本文档主要说明任务队列通用模型和 `/task` 相关接口。

---

## 一、总体说明

- **基础地址**：`http://<host>:<port>`，开发环境常见为 `http://localhost:8000`
- **接口风格**：RESTful
- **任务队列模式**：
  - 所有耗时操作（转写、VAD、BGM 分离）均采用异步任务队列；
  - 创建任务接口返回一个 `identifier`，前端需基于此调用任务查询接口轮询获取结果。

---

## 二、统一枚举

### 1. TaskStatus（任务状态）

```text
pending
queued
in_progress
completed
failed
cancelled
paused
retrying
```

### 2. TaskType（任务类型）

```text
transcription
vad
bgm_separation
```

### 3. ResultType（结果类型）

```text
json      # result 是 JSON 数据
filepath  # result 里保存的是文件路径信息（通常需要再调下载接口）
```

---

## 三、通用响应模型

### 1. QueueResponse（排队响应）

**出现位置**：所有“创建任务”的 POST 接口返回值（转写、VAD、BGM 分离）。

```json
{
  "identifier": "string",  // 任务唯一 ID
  "status": "queued",      // 当前任务状态，初始通常为 queued
  "message": "Transcription task has queued"
}
```

字段说明：

- `identifier`：字符串，后续轮询 `/task/{identifier}` 的关键；
- `status`：任务当前状态（`TaskStatus` 枚举之一）；
- `message`：人类可读提示信息。

### 2. TaskStatusResponse（任务状态查询）

**出现位置**：`GET /task/{identifier}`。

```json
{
  "identifier": "string",
  "status": "in_progress | completed | failed | ...",
  "task_type": "transcription | vad | bgm_separation",
  "result_type": "json | filepath",
  "result": {},
  "task_params": {},
  "error": "string or null",
  "duration": 12.34,
  "progress": 0.0
}
```

字段说明：

- `identifier`：任务 ID；
- `status`：当前任务状态（如 `queued`、`in_progress`、`completed`、`failed` 等）；
- `task_type`：任务类型（`transcription` / `vad` / `bgm_separation`）；
- `result_type`：结果类型（`json` / `filepath`）；
- `result`：任务结果内容，结构随任务类型而不同；
- `task_params`：创建任务时的参数快照，方便调试或重放；
- `error`：失败时的错误消息，成功任务通常为 `null` 或空；
- `duration`：任务执行耗时（秒）；
- `progress`：进度，范围 `0.0 ~ 1.0`。

---

## 四、任务查询与结果下载

### 1. 查询任务状态

- **方法**：GET
- **路径**：`/task/{identifier}`
- **描述**：根据 `identifier` 查询指定任务当前状态、结果等信息。

#### 路径参数

- `identifier`：字符串，创建任务时返回的任务 ID。

#### 成功响应

- 状态码：`200 OK`
- Body：`TaskStatusResponse`（见上）。

#### 可能的错误

- `404 Not Found`：任务不存在（identifier 错误或任务已被删除）。

---

### 2. 下载 BGM 分离结果文件

> 仅对 `task_type = bgm_separation` 的任务有效。

- **方法**：GET
- **路径**：`/task/file/{identifier}`
- **描述**：基于 BGM 分离任务的 `identifier` 下载压缩后的分离音频文件（ZIP）。

#### 路径参数

- `identifier`：BGM 分离任务的 ID。

#### 成功响应

- 状态码：`200 OK`
- Headers：`Content-Type: application/zip`
- Body：ZIP 文件（二进制流），通常包含：
  - 伴奏文件（instrumental）；
  - 人声文件（vocals）。

#### 失败情况

- `404 Not Found`：identifier 不存在，或任务类型不是 `bgm_separation`。

---

## 五、前端对接建议

1. 创建任务接口只负责返回 `identifier` 与初始 `status`，不要指望立即拿到完整结果；
2. 前端统一封装 `pollTask(identifier)` 工具，按需配置轮询间隔和最大次数；
3. 根据 `task_type` 和 `result_type` 解析结果：
   - `transcription`：`result` 为字幕分段数组；
   - `vad`：`result` 为语音区间数组；
   - `bgm_separation`：`result` 为哈希信息，需结合 `/task/file/{identifier}` 下载 ZIP 文件。
