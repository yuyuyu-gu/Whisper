## Face Search 前端接口文档

后端 router：`backend/routers/face_search/router.py`

- 统一前缀：`/face-search`
- 所有接口返回 JSON，错误场景通常通过 HTTP 状态码 4xx/5xx + `detail` 字段返回。

---

### 1. 图片入库（索引单张图片）

- **方法**：`POST`
- **路径**：`/face-search/index`
- **请求类型**：`multipart/form-data`

**请求体字段**：

| 字段名 | 类型 | 必填 | 说明 |
| ------ | ---- | ---- | ---- |
| `file` | file | 是  | 要入库的人脸图片（jpg/png/webp 等） |

**成功响应（200）**：

```json
{
  "success": true,
  "processed_images": 1,
  "total_faces": 2,
  "errors": [],
  "message": "已入库。"
}
```

当未检测到人脸或文件已存在索引中时：

```json
{
  "success": false,
  "processed_images": 0,
  "total_faces": 0,
  "errors": ["未检测到有效人脸或文件已存在索引中。"],
  "message": "未检测到有效人脸或文件已存在索引中。"
}
```

**前端使用要点**：

- 使用 `FormData` 提交：`formData.append("file", file)`。
- 根据 `success` 和 `message` 给出入库结果提示。

---

### 2. 使用图片检索相似人脸

- **方法**：`POST`
- **路径**：`/face-search/query`
- **请求类型**：`multipart/form-data`

**请求体字段**：

| 字段名            | 类型 | 必填 | 说明 |
|-------------------|------|------|------|
| `file`            | file | 是   | 查询图片 |
| `top_k`           | int  | 否   | 返回前多少条结果，默认 5 |
| `score_threshold` | float| 否   | 距离阈值（越小越相似），默认 0.8 |

> `score_threshold` 在后端作为“最大距离”使用，超过该距离的结果会被过滤。

**成功响应（200）**：

```json
{
  "success": true,
  "matches": [
    {
      "image_path": "path/to/indexed/image1.jpg",
      "distance": 0.15,
      "original_path": null
    }
  ]
}
```

字段说明：

- `matches`：按相似度从高到低（距离从小到大）排列；
- `image_path`：后端保存的图片路径（前端可视部署时按需拼接静态前缀）；
- `distance`：向量距离，数值越小越相似；
- `original_path`：当前实现中为 `null`，预留字段。

**可能的错误响应**：

- 当图片无效/内部错误时，返回 HTTP 400 或 500：

```json
{
  "detail": "错误描述信息"
}
```

**前端使用要点**：

- 同样用 `FormData` 上传 `file`，`top_k`、`score_threshold` 以表单字段方式传递；
- 可将 `distance` 转换为相似度得分，例如 `score = 1 - distance`，用于显示。

---

### 3. 查询人脸库统计信息

- **方法**：`GET`
- **路径**：`/face-search/stats`

**成功响应（200）**：

```json
{
  "total_faces": 5000,
  "total_images": 120,
  "total_indexed_files": 300
}
```

字段说明：

- `total_faces`：当前向量库中记录的人脸总数；
- `total_images`：参与索引的唯一图像数量；
- `total_indexed_files`：已索引过的文件数量（包含去重前的信息）。

**前端使用要点**：

- 适合在管理后台显示统计指标或健康度信息。

---

### 4. 清空人脸数据库（危险操作）

- **方法**：`POST`
- **路径**：`/face-search/reset`

**请求体（JSON）**：

```json
{
  "confirm": true
}
```

若 `confirm` 不为 `true`：

```json
{
  "success": false,
  "message": "请显式确认 confirm=true 以执行清空操作。",
  "deleted_faces": null,
  "deleted_records": null,
  "errors": null
}
```

清空成功示例：

```json
{
  "success": true,
  "message": "人脸数据库已清空。",
  "deleted_faces": null,
  "deleted_records": null,
  "errors": null
}
```

**前端使用要点**：

- 仅在管理后台暴露此接口；
- 建议二次确认弹窗，明确提示不可恢复。

---

### 5. 删除指定图片对应的人脸记录

- **方法**：`POST`
- **路径**：`/face-search/delete-images`

**请求体（JSON）**：

```json
{
  "image_paths": [
    "path/to/indexed/image1.jpg",
    "path/to/indexed/image2.jpg"
  ]
}
```

**成功响应（200）**：

```json
{
  "success": true,
  "message": "删除完成。",
  "deleted_faces": 42,
  "deleted_records": null,
  "errors": []
}
```

**前端使用要点**：

- 主要用于管理页面批量删除错误入库的图片记录；
- `image_paths` 应与检索结果返回的 `image_path` 对应。

---

### 6. 清理“孤儿”索引记录

- **方法**：`POST`
- **路径**：`/face-search/cleanup-orphans`

**请求体**：无

**成功响应（200）**：

```json
{
  "success": true,
  "message": "孤儿记录清理完成。",
  "deleted_faces": null,
  "deleted_records": 10,
  "errors": []
}
```

**前端使用要点**：

- 可在运维工具或后台管理中提供“一键清理”入口；
- 正常业务页面一般不需要暴露此操作。

---

### 7. 错误与异常处理建议

- 上传类接口请处理好以下情况：
  - HTTP 400：文件缺失、不合法图片、无脸等；
  - HTTP 500：服务内部错误；
- 建议统一封装一个请求工具：
  - 成功时按上面的数据模型解析；
  - 失败时读取 `error.response?.data.detail` 或 `message` 进行提示。
