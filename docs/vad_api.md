# 语音活动检测 / VAD API 文档

后端 router：`backend/routers/vad/router.py`

> 本文档仅描述 `/vad` 相关接口，任务排队与查询模型见 `task_api.md`。

---

## 一、创建 VAD 任务

- **方法**：POST
- **路径**：`/vad/`
- **标签**：`Voice Activity Detection`
- **描述**：对上传的音频/视频文件执行语音活动检测，输出语音区间时间线。
- **请求 Content-Type**：`multipart/form-data`

### 1. 请求体字段

1）文件字段

- 字段名：`file`
- 类型：文件（二进制）
- 说明：音频或视频文件。

2）查询参数（VadParams，与转写内部使用的同一套）

- `vad_filter`：`boolean`，默认 `false`；
- `threshold`：`number`，默认 `0.5`；
- `min_speech_duration_ms`：`number`，默认 `250`；
- `max_speech_duration_s`：`number`，默认 `inf`；
- `min_silence_duration_ms`：`number`，默认 `2000`；
- `speech_pad_ms`：`number`，默认 `400`。

---

## 二、响应说明

### 1. 创建任务响应

- 状态码：`201 Created`
- Body：`QueueResponse`（见 `task_api.md`）。

```json
{
  "identifier": "xxx",
  "status": "queued",
  "message": "VAD task has queued"
}
```

### 2. 任务完成后的结果结构

当通过 `GET /task/{identifier}` 查询到：

- `task_type = "vad"`
- `status = "completed"`

时：

- `result` 为 `speech_chunks` 列表，每个元素是一个字典：

```json
[
  { "start": 1600, "end": 6400 },
  { "start": 8000, "end": 12000 }
]
```

说明：

- 采样率固定为 `16000 Hz`；
- `start` / `end` 为采样点索引（sample index）；
- 对应时间（秒） = `index / 16000`。

前端可用这些时间段：

- 在波形图/进度条上高亮出“有声”片段；
- 联动播放器 `currentTime` 做可视化提示。
