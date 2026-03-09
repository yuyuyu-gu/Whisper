# 背景音乐分离 / BGM Separation API 文档

后端 router：`backend/routers/bgm_separation/router.py`

> 本文档描述 `/bgm-separation` 相关接口，任务排队与查询模型见 `task_api.md`。

---

## 一、创建 BGM 分离任务

- **方法**：POST
- **路径**：`/bgm-separation/`
- **标签**：`BGM Separation`
- **描述**：将上传的音频/视频中的人声与伴奏分离。
- **请求 Content-Type**：`multipart/form-data`

### 1. 请求体字段

1）文件字段

- 字段名：`file`
- 类型：文件（二进制）
- 说明：音频或视频文件。

2）查询参数（BGMSeparationParams，与转写内部使用的同一套）

> 为了真正触发分离操作，通常需要将 `is_separate_bgm` 设为 `true`。

- `is_separate_bgm`：`boolean`，默认 `false`，是否启用 BGM 分离；
- `uvr_model_size`：`string`，默认 `"UVR-MDX-NET-Inst_HQ_4"`，UVR 模型名；
- `uvr_device`：`string`，默认 `"cuda"`，可选 `"cpu"` / `"cuda"` / `"xpu"`；
- `segment_size`：`number`，默认 `256`，分段大小；
- `save_file`：`boolean`，默认 `false`，是否持久化分离后的音频文件；
- `enable_offload`：`boolean`，默认 `true`，任务结束后是否卸载模型。

---

## 二、响应说明

### 1. 创建任务响应

- 状态码：`201 Created`
- Body：`QueueResponse`（见 `task_api.md`）。

```json
{
  "identifier": "xxx",
  "status": "queued",
  "message": "BGM Separation task has queued"
}
```

### 2. 任务完成后的结果结构

当通过 `GET /task/{identifier}` 查询到：

- `task_type = "bgm_separation"`
- `status = "completed"`

时：

- `result_type = "filepath"`
- `result` 字段结构：

```json
{
  "instrumental_hash": "string",
  "vocal_hash": "string"
}
```

> 真实文件路径由后端在缓存目录中通过哈希查找，不直接暴露在此 JSON 中。

如需下载实际音频文件，请调用：

- `GET /task/file/{identifier}`（详见 `task_api.md`）。

返回值为 ZIP 文件，通常包含：

- 伴奏音轨（instrumental）；
- 人声音轨（vocals）。
