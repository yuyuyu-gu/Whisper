## 二、图像检索接口（Face Search）

- 推荐统一前缀：`/face-search`
- 后端内部实现建议基于 `modules/face_search/service.py` 中的 `FaceSearchService`。

### 1. 索引（入库）单张图片

- **方法**：`POST`
- **路径**：`/face-search/index`
- **请求类型**：`multipart/form-data`

- **请求体字段**：

| 字段名 | 类型 | 必填 | 说明 |
| ------ | ---- | ---- | ---- |
| `file` | file | 是  | 图片文件（jpg/png/webp 等） |
| `meta` | string(JSON) | 否 | 附加信息（人物姓名、说明文本等） |

- **成功响应示例**：

```json
{
  "success": true,
  "id": "face_123456",       
  "faces_count": 2,
  "message": "已入库。"
}
```

- **失败响应示例**（格式不支持、文件损坏等）：

```json
{
  "success": false,
  "message": "不支持的图像格式: .gif。支持的格式: .jpg, .png, .bmp, .webp, .jfif, .tiff, .tif"
}
```

> 入库过程中会做：文件存在性检查、大小检查、图像解码验证、最小尺寸检查，以及 MD5 去重等。

---

### 2. 使用图片进行人脸检索

- **方法**：`POST`
- **路径**：`/face-search/query`
- **请求类型**：`multipart/form-data`

- **请求体字段**：

| 字段名           | 类型 | 必填 | 说明 |
|------------------|------|------|------|
| `file`           | file | 是   | 用于检索的查询图片 |
| `top_k`          | int  | 否   | 返回前多少条最相似结果，默认 5 |
| `score_threshold`| float| 否   | 相似度阈值（如 0.3~0.9），低于该值可不返回 |

- **成功响应示例**：

```json
{
  "success": true,
  "matches": [
    {
      "id": "face_123456",
      "score": 0.92,
      "meta": {
        "name": "张三",
        "desc": "1980 届校友，曾任学生会主席"
      },
      "image_path": "/static/face_db/images/xxx.jpg"
    },
    {
      "id": "face_789012",
      "score": 0.88,
      "meta": null,
      "image_path": "/static/face_db/images/yyy.jpg"
    }
  ]
}
```

- **未命中或得分过低时**：

```json
{
  "success": true,
  "matches": []
}
```

> 内部逻辑：读取查询图片 → 检测人脸 → 提取向量 → 使用 ChromaDB 按余弦相似度进行检索 → 组装结果返回。

---

### 3. 检索库统计信息（可选）

- **方法**：`GET`
- **路径**：`/face-search/stats`

- **响应示例**：

```json
{
  "images_count": 120,
  "faces_count": 5000,
  "db_dir": "face_db"
}
```

> 用于前端展示“当前人脸库规模”的概览信息。

---

### 4. 清空检索库（仅管理员，可选）

- **方法**：`POST`
- **路径**：`/face-search/reset`
- **请求体（JSON，可选确认字段）**：

```json
{
  "confirm": true
}
```

- **响应示例**：

```json
{
  "success": true,
  "message": "人脸数据库已清空。"
}
```

> 内部可调用 `FaceSearchService` 的重置方法，清理图片文件目录和 ChromaDB 存储。

---