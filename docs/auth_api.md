# 后端 REST 接口建议文档（认证）

## 一、认证与用户审批接口（Auth）

- 推荐统一前缀：`/auth`
- 后端内部实现建议基于 `services/auth/service.py` 中的 `AuthService`。

### 1. 用户注册

- **方法**：`POST`
- **路径**：`/auth/register`
- **请求体（JSON）**：

```json
{
  "username": "string",
  "password": "string"
}
```

- **成功响应（JSON）示例**：

```json
{
  "success": true,
  "message": "注册成功！test_user 已提交审核，请等待管理员批准。"
}
```

- **失败响应示例**：

```json
{
  "success": false,
  "message": "用户名和密码均不能为空。"
}
```

> 对应 `AuthService.register_user(username, password)`。

---

### 2. 用户登录

- **方法**：`POST`
- **路径**：`/auth/login`
- **请求体（JSON）**：

```json
{
  "username": "string",
  "password": "string"
}
```

- **成功响应（JSON）示例**：

```json
{
  "success": true,
  "role": "admin",          // 或 "user"
  "message": "欢迎，test_user！"
}
```

- **失败响应示例**（账号未激活、密码错误等）：

```json
{
  "success": false,
  "role": null,
  "message": "该账号尚未通过管理员审核。"
}
```

> 对应 `AuthService.login_user(username, password)`。
> 如需会话/鉴权，可在此接口扩展返回 `token` 字段。  

---

### 3. 获取待审核用户列表（管理员）

- **方法**：`GET`
- **路径**：`/auth/pending`
- **请求参数**：无（建议配合登录态，仅管理员可调用）。

- **响应（JSON）示例**：

```json
{
  "pending": [
    "user1",
    "user2"
  ]
}
```

> 对应 `AuthService.get_pending_users()`。

---

### 4. 审批通过用户（管理员）

- **方法**：`POST`
- **路径**：`/auth/approve`
- **请求体（JSON）**：

```json
{
  "username": "user1"
}
```

- **成功响应示例**：

```json
{
  "success": true,
  "message": "用户 user1 已成功激活。"
}
```

- **失败响应示例**：

```json
{
  "success": false,
  "message": "未找到该用户或该用户已被审核。"
}
```

> 对应 `AuthService.approve_user(username)`。

---

### 5. 获取用户列表（不含默认管理员）

- **方法**：`GET`
- **路径**：`/auth/users`

- **响应（JSON）示例**：

```json
{
  "users": [
    {
      "username": "alice",
      "role": "user",
      "status": "active"      // 或 "pending"
    },
    {
      "username": "bob",
      "role": "admin",
      "status": "active"
    }
  ]
}
```

> 对应 `AuthService.get_all_users()`。

---

### 6. 赋予管理员权限（仅主账号）

- **方法**：`POST`
- **路径**：`/auth/grant-admin`
- **请求体（JSON）**：

```json
{
  "target_username": "alice",      // 需要提升为管理员的用户
  "current_username": "admin"      // 当前操作人用户名
}
```

- **成功响应示例**：

```json
{
  "success": true,
  "message": "已成功将 alice 设置为管理员。"
}
```

- **失败响应示例**：

```json
{
  "success": false,
  "message": "只有主账号可以赋予管理员权限。"
}
```

> 对应 `AuthService.grant_admin_role(target_username, current_username)`。

---

### 7. 撤销管理员权限（仅主账号）

- **方法**：`POST`
- **路径**：`/auth/revoke-admin`
- **请求体（JSON）**：

```json
{
  "target_username": "alice",      // 要撤销管理员权限的用户
  "current_username": "admin"      // 当前操作人用户名
}
```

- **成功响应示例**：

```json
{
  "success": true,
  "message": "已成功将 alice 的管理员权限撤销。"
}
```

> 对应 `AuthService.revoke_admin_role(target_username, current_username)`。

---

## 三、前后端对接建议

1. **路径与字段保持稳定**：
   - 一旦前端开始使用这些接口，尽量避免随意更改 URL 和字段名；若需调整，可增加新版本路径（如 `/auth/v2/...`）。

2. **管理员权限控制**：
   - 建议给 `/auth/pending`、`/auth/approve`、`/auth/grant-admin`、`/auth/revoke-admin`、`/face-search/reset` 等接口增加登录校验与角色判断。

3. **错误码与 message**：
   - 统一约定：`success` + `message` 为前端展示主依据，必要时可补充 `code` 字段便于前端做细粒度处理。

4. **静态文件访问路径**：
   - 图像检索返回的 `image_path` 建议统一映射到可访问的静态路由（例如 `/static/...`），前端可直接展示缩略图。
