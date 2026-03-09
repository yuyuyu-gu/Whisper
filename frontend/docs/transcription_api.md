# 语音转写 / Transcription API 文档

后端 router：`backend/routers/transcription/router.py`

> 本文档仅描述 `/transcription` 相关转写接口，任务排队与查询模型见 `task_api.md`。

---

## 一、创建转写任务

- **方法**：POST
- **路径**：`/transcription/`
- **标签**：`Transcription`
- **描述**：上传音频/视频文件，创建异步语音转写任务。
- **请求 Content-Type**：`multipart/form-data`

### 1. 请求体字段

1）文件字段

- 字段名：`file`
- 类型：文件（二进制）
- 说明：音频或视频文件，后端自动解码。

2）查询参数（WhisperParams，转写参数）

> 所有参数均为 Query 参数，不传时使用默认值。下面列出后端当前支持的全部字段。

基础参数：

- `model_size`：`string`，默认 `"large-v2"`，Whisper 模型大小；
- `lang`：`string?`，语言代码，如 `"en"`、`"zh"`，为空或特殊值时表示自动检测；
- `is_translate`：`boolean`，默认 `false`，是否将语音直接翻译为英文；

解码与搜索相关：

- `beam_size`：`number`，默认 `5`，解码 beam 大小；
- `log_prob_threshold`：`number`，默认 `-1.0`，采样 token 的平均 log 概率阈值；
- `no_speech_threshold`：`number`，范围 `0~1`，默认 `0.6`，静音检测阈值；
- `best_of`：`number`，默认 `5`，采样模式下保留多少候选；
- `patience`：`number`，默认 `1.0`，beam search 的耐心参数；

计算精度与批处理：

- `compute_type`：`string`，默认 `"float16"`，推理精度，比如 `"float16"` / `"int8"` / `"int16"`；
- `batch_size`：`number`，默认 `24`，批大小；

提示词与上下文：

- `condition_on_previous_text`：`boolean`，默认 `true`，是否将上一窗口的输出作为下一窗口的提示；
- `prompt_reset_on_temperature`：`number`，范围 `0~1`，默认 `0.5`，温度高于该值时重置提示；
- `initial_prompt`：`string?`，首个窗口使用的初始提示词；
- `prefix`：`string?`，首个窗口前缀文本；
- `hotwords`：`string?`，提示词 / 热词，提升特定词汇识别；

采样与长度控制：

- `temperature`：`number`，默认 `0.0`，采样温度；
- `compression_ratio_threshold`：`number`，默认 `2.4`，gzip 压缩比阈值；
- `length_penalty`：`number`，默认 `1.0`，长度惩罚因子；
- `repetition_penalty`：`number`，默认 `1.0`，重复 token 惩罚；
- `no_repeat_ngram_size`：`number`，默认 `0`，n-gram 尺寸，大于 0 时避免重复 n-gram；
- `max_new_tokens`：`number?`，默认 `null`，每个 chunk 允许生成的新 token 上限；

时间与标点处理：

- `max_initial_timestamp`：`number`，默认 `1.0`，首个时间戳最大值；
- `word_timestamps`：`boolean`，默认 `false`，是否输出逐词时间戳；
- `prepend_punctuations`：`string?`，默认 `""'“¿([{-"`，哪些标点与后一个词合并；
- `append_punctuations`：`string?`，默认 `""'.。,，!！?？:：”)]}、"`，哪些标点与前一个词合并；
- `chunk_length`：`number?`，默认 `30`，按秒切分的音频片段长度；
- `hallucination_silence_threshold`：`number?`，默认 `null`，幻觉检测中跳过静音片段的阈值；

语言检测：

- `language_detection_threshold`：`number?`，默认 `0.5`，语言检测概率阈值；
- `language_detection_segments`：`number`，默认 `1`，参与语言检测的片段数；

其他控制：

- `suppress_blank`：`boolean`，默认 `true`，是否在采样开始阶段抑制空白输出；
- `suppress_tokens`：`string | int[]`，默认 `[-1]`，需要抑制的 token ID 列表。前端可以传字符串形式的数组（例如 `"[-1, 2, 3]"`），后端会解析；
- `enable_offload`：`boolean`，默认 `true`，转写结束后是否卸载 Whisper 模型。

3）查询参数（VadParams，VAD 相关）

> 这些参数控制在**转写流水线内部**是否及如何应用 VAD（裁剪静音）。

- `vad_filter`：`boolean`，默认 `false`，是否启用 VAD 过滤静音；
- `threshold`：`number`，范围 `0~1`，默认 `0.5`，VAD 概率阈值；
- `min_speech_duration_ms`：`number`，默认 `250`，小于此长度的语音片段将被丢弃（毫秒）；
- `max_speech_duration_s`：`number`，默认 `inf`，单段语音最大长度（秒）；
- `min_silence_duration_ms`：`number`，默认 `2000`，语音片段之间最短静音间隔（毫秒）；
- `speech_pad_ms`：`number`，默认 `400`，在语音片段两侧填充的时长（毫秒）。

4）查询参数（BGMSeparationParams，转写中的 BGM 预处理）

> 注意：这是**转写流水线内部**的 BGM 分离开关，与单独的 `/bgm-separation` 接口不同。

- `is_separate_bgm`：`boolean`，默认 `false`，是否在转写前先尝试 BGM 分离；
- `uvr_model_size`：`string`，默认 `"UVR-MDX-NET-Inst_HQ_4"`，UVR 模型名；
- `uvr_device`：`string`，默认 `"cuda"`，设备（如 `"cpu"` / `"cuda"` / `"xpu"`）；
- `segment_size`：`number`，默认 `256`，分段大小；
- `save_file`：`boolean`，默认 `false`，是否保存分离后的文件；
- `enable_offload`：`boolean`，默认 `true`，任务结束后是否卸载模型。

5）查询参数（DiarizationParams，说话人分离）

- `is_diarize`：`boolean`，默认 `false`，是否进行说话人分离；
- `diarization_device`：`string`，默认 `"cuda"`，设备；
- `hf_token`：`string?`，下载 diarization 模型时所需的 HuggingFace token（首次使用时需要）；
- `enable_offload`：`boolean`，默认 `true`，结束后是否卸载模型。

---

## 二、响应说明

### 1. 创建任务响应

- 状态码：`201 Created`
- Body：`QueueResponse`（见 `task_api.md`）。

```json
{
  "identifier": "b1c0c6c4-...-...",
  "status": "queued",
  "message": "Transcription task has queued"
}
```

### 2. 任务完成后的结果结构

当通过 `GET /task/{identifier}` 查询到：

- `task_type = "transcription"`
- `status = "completed"`

时：

- `result` 字段为 `Segment` 列表。

`Segment`（简化）示例：

```json
{
  "id": 0,
  "seek": 0,
  "text": "Hello world",
  "start": 0.0,
  "end": 1.23,
  "tokens": [1, 2, 3],
  "temperature": 0.0,
  "avg_logprob": -0.1,
  "compression_ratio": 1.2,
  "no_speech_prob": 0.01,
  "words": [
    {
      "start": 0.0,
      "end": 0.5,
      "word": "Hello",
      "probability": 0.95
    }
  ]
}
```

前端典型用法：

- 将 `result` 按 `start/end` 渲染为时间轴字幕；
- 或导出为 SRT/VTT 等字幕文件格式。
