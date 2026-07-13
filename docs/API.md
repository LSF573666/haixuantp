# 海选投票 API 接口文档

> 基础地址: `http://localhost:8000`  
> 认证方式: JWT Bearer Token  
> OpenAPI YAML: [openapi.yaml](./openapi.yaml)  
> 在线文档: `/api/docs/` (Swagger UI) | `/api/redoc/` (ReDoc)

---

## 通用说明

### 请求头

需要鉴权的接口请在 Header 中携带:

```
Authorization: Bearer <access_token>
```

JSON 请求使用 `Content-Type: application/json`；报名提交支持 JSON（OSS 直传后传 `avatar_url`）或 `multipart/form-data`（文件上传）。

### 统一错误响应

```json
{
  "detail": "错误描述信息"
}
```

### 分页响应格式

列表接口默认每页 20 条:

```json
{
  "count": 100,
  "next": "http://localhost:8000/api/xxx/?page=2",
  "previous": null,
  "results": []
}
```

---

## 接口总览

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| 认证 | `/api/auth/` | 短信注册/登录、Token 刷新、用户信息 |
| 候选人 | `/api/candidates/` | 候选人列表、详情、排行榜 |
| 报名 | `/api/candidates/applications/` | 自主报名、查询审核进度 |
| 投票 | `/api/votes/` | 投票状态、投票、投票记录 |
| 礼物 | `/api/gifts/` | 礼物列表、赠送、赠送记录 |
| 支付 | `/api/payments/` | 充值、订单、支付回调 |
| 配置 | `/api/config/` | 公开系统配置、OSS STS 上传凭证 |

> 兼容无前缀访问（如 `/auth/login/`），推荐使用 `/api/` 前缀。

---

## 1. 认证模块 `/api/auth/`

| 接口 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/auth/sms/send/` | POST | 否 | 发送短信验证码 |
| `/api/auth/register/` | POST | 否 | 新用户注册 |
| `/api/auth/login/` | POST | 否 | 手机号验证码登录 |
| `/api/auth/login/password/` | POST | 否 | 手机号密码登录 |
| `/api/auth/password/set/` | POST | 是 | 设置/修改登录密码 |
| `/api/auth/token/refresh/` | POST | 否 | 刷新 Token |
| `/api/auth/profile/` | GET / PATCH | 是 | 获取/更新用户信息 |

### 1.1 发送短信验证码

- **URL**: `POST /api/auth/sms/send/`
- **鉴权**: 不需要

**请求体:**

```json
{
  "phone": "13800138000"
}
```

**成功响应 (200):**

```json
{
  "message": "验证码已发送",
  "phone": "13800138000"
}
```

> 开发模式下验证码固定为 `123456`（可在 `.env` 中配置 `SMS_DEV_CODE`）

---

### 1.2 新用户注册

- **URL**: `POST /api/auth/register/`
- **鉴权**: 不需要

**请求体:**

```json
{
  "phone": "13800138000",
  "code": "123456",
  "nickname": "新用户",
  "password": "your_password"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `phone` | string | 是 | 手机号 |
| `code` | string | 是 | 短信验证码（需先调用发送验证码接口） |
| `nickname` | string | 否 | 昵称 |
| `password` | string | 否 | 登录密码，注册时可直接设置 |

**成功响应 (201):**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "phone": "13800138000",
    "nickname": "新用户",
    "avatar": null,
    "balance": "0.00",
    "has_password": true,
    "created_at": "2026-07-13 10:00:00"
  },
  "is_new_user": true
}
```

**错误响应 (400):**

手机号已注册:

```json
{
  "phone": ["该手机号已注册"]
}
```

验证码错误:

```json
{
  "detail": "验证码错误或已过期"
}
```

> 注册须先获取短信验证码。注册成功后自动登录，返回 JWT Token。若未设置密码，可后续通过「设置/修改登录密码」接口补充（同样需短信验证码）。

---

### 1.3 手机号登录

- **URL**: `POST /api/auth/login/`
- **鉴权**: 不需要

**请求体:**

```json
{
  "phone": "13800138000",
  "code": "123456"
}
```

**成功响应 (200):**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "phone": "13800138000",
    "nickname": "",
    "avatar": null,
    "balance": "0.00",
    "has_password": false,
    "created_at": "2026-07-09 14:00:00"
  },
  "is_new_user": true
}
```

---

### 1.4 密码登录

- **URL**: `POST /api/auth/login/password/`
- **鉴权**: 不需要

**请求体:**

```json
{
  "phone": "13800138000",
  "password": "your_password"
}
```

**成功响应 (200):** 与验证码登录相同，返回 `access`、`refresh`、`user`、`is_new_user`（密码登录时 `is_new_user` 恒为 `false`）。

**错误响应 (400):**

```json
{
  "detail": "手机号或密码错误"
}
```

> 需先通过验证码登录并完成密码设置后，方可使用密码登录。

---

### 1.5 设置/修改登录密码

- **URL**: `POST /api/auth/password/set/`
- **鉴权**: 需要

**流程**: 先调用 `POST /api/auth/sms/send/` 向当前账号手机号发送验证码，再提交验证码和新密码。

**请求体:**

```json
{
  "code": "123456",
  "password": "your_new_password"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | string | 是 | 短信验证码（需先调用发送验证码接口，发送到当前登录用户手机号） |
| `password` | string | 是 | 新密码 |

**成功响应 (200):**

```json
{
  "message": "密码设置成功"
}
```

**错误响应 (400):**

验证码错误:

```json
{
  "detail": "验证码错误或已过期"
}
```

> 首次设置和修改密码均须短信验证码。密码须满足 Django 默认强度要求（至少 8 位，不能过于常见等）。用户信息中的 `has_password` 字段表示是否已设置登录密码。

---

### 1.6 刷新 Token

- **URL**: `POST /api/auth/token/refresh/`

**请求体:**

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

### 1.7 获取/更新用户信息

- **URL**: `GET /api/auth/profile/` | `PATCH /api/auth/profile/`
- **鉴权**: 需要

---

## 2. 候选人模块 `/api/candidates/`

| 接口 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/candidates/` | GET | 否 | 候选人列表 |
| `/api/candidates/{id}/` | GET | 否 | 候选人详情（含照片） |
| `/api/candidates/ranking/` | GET | 否 | 热度排行榜 |

---

## 2.1 报名模块 `/api/candidates/applications/`

用户自主报名参加海选，提交后由后台审核。前端可通过「查询报名进度」接口获取审核状态与反馈文案。

| 接口 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/candidates/applications/submit/` | POST | 是 | 提交/重新提交报名 |
| `/api/candidates/applications/status/` | GET | 是 | 查询我的报名进度 |

### 2.1.1 提交报名申请

- **URL**: `POST /api/candidates/applications/submit/`
- **鉴权**: 需要
- **Content-Type**: `multipart/form-data` 或 `application/json`

**请求字段:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 姓名 |
| `introduction` | string | 否 | 个人介绍 |
| `avatar` | file | 首次二选一 | 头像文件上传（与 `avatar_url` 二选一） |
| `avatar_url` | string | 首次二选一 | OSS 直传后的头像完整 URL，须在当前用户目录 `uploads/{user_id}/` 下 |
| `photos` | file[] | 否 | 展示照片，可上传多张；驳回后重新提交可不传，保留上次照片 |

**JSON 请求示例（OSS 直传后）:**

```json
{
  "name": "张三",
  "introduction": "热爱舞台，期待展示自我",
  "avatar_url": "https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/12/avatar.jpg"
}
```

**multipart 请求示例（OSS 直传后）:**

```
name=张三
introduction=热爱舞台
avatar_url=https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/12/avatar.jpg
```

**成功响应 (201):**

```json
{
  "id": 1,
  "name": "张三",
  "introduction": "热爱舞台，期待展示自我",
  "avatar": "/media/applications/avatars/xxx.jpg",
  "photos": [
    {
      "id": 1,
      "image": "/media/applications/photos/xxx.jpg",
      "caption": "",
      "sort_order": 0
    }
  ],
  "status": "pending",
  "status_display": "待审核",
  "status_message": "您的报名申请已提交，正在审核中，请耐心等待",
  "reject_reason": "",
  "candidate_id": null,
  "created_at": "2026-07-10 10:00:00",
  "updated_at": "2026-07-10 10:00:00",
  "reviewed_at": null
}
```

**业务规则:**

- 每位用户同时只能有一条待审核申请
- 审核通过后不可重复报名，自动创建候选人并展示在候选人列表/排行榜中
- 被驳回后可修改资料重新提交；头像和照片可不传，将保留上次内容

**重新提交（驳回后）请求示例:**

仅修改姓名和介绍，无需重新上传头像/照片：

```
name=李四
introduction=更新后的个人介绍
```

**错误响应 (400):**

```json
{
  "detail": "您已有待审核的报名申请，请耐心等待审核结果"
}
```

---

### 2.1.2 查询我的报名进度

- **URL**: `GET /api/candidates/applications/status/`
- **鉴权**: 需要

**成功响应 (200) — 已提交报名:**

```json
{
  "has_application": true,
  "can_apply": false,
  "can_resubmit": false,
  "is_candidate": false,
  "resubmit_hint": "",
  "application": {
    "id": 1,
    "name": "张三",
    "introduction": "热爱舞台，期待展示自我",
    "avatar": "/media/applications/avatars/xxx.jpg",
    "photos": [],
    "status": "pending",
    "status_display": "待审核",
    "status_message": "您的报名申请已提交，正在审核中，请耐心等待",
    "reject_reason": "",
    "candidate_id": null,
    "created_at": "2026-07-10 10:00:00",
    "updated_at": "2026-07-10 10:00:00",
    "reviewed_at": null
  }
}
```

**审核通过时** `status` 为 `approved`，`is_candidate` 为 `true`，`candidate_id` 返回关联的候选人 ID，该候选人会出现在 `/api/candidates/` 列表和排行榜中。

**审核驳回时** `status` 为 `rejected`，`can_apply` 和 `can_resubmit` 为 `true`，`resubmit_hint` 为 `"资料被驳回，请修改姓名、介绍或照片后重新提交"`，`status_message` 包含驳回原因。

**审核驳回响应示例:**

```json
{
  "has_application": true,
  "can_apply": true,
  "can_resubmit": true,
  "is_candidate": false,
  "resubmit_hint": "资料被驳回，请修改姓名、介绍或照片后重新提交",
  "application": {
    "status": "rejected",
    "status_display": "已驳回",
    "status_message": "审核未通过，请根据反馈修改资料后重新提交。驳回原因：照片不清晰",
    "reject_reason": "照片不清晰",
    "candidate_id": null
  }
}
```

**审核通过响应示例:**

```json
{
  "has_application": true,
  "can_apply": false,
  "can_resubmit": false,
  "is_candidate": true,
  "resubmit_hint": "",
  "application": {
    "status": "approved",
    "status_display": "已通过",
    "status_message": "恭喜！您的报名申请已通过审核，您已成为候选人，可在候选人列表中查看",
    "candidate_id": 5
  }
}
```

**未提交过报名时:**

```json
{
  "has_application": false,
  "can_apply": true,
  "can_resubmit": false,
  "is_candidate": false,
  "resubmit_hint": "",
  "application": null
}
```

**状态枚举:**

| status | status_display | 说明 |
|--------|----------------|------|
| `pending` | 待审核 | 已提交，等待后台审核 |
| `approved` | 已通过 | 审核通过，已创建候选人 |
| `rejected` | 已驳回 | 审核未通过，可重新提交 |

---

## 3. 投票模块 `/api/votes/`

| 接口 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/votes/status/` | GET | 是 | 查询今日投票状态 |
| `/api/votes/cast/` | POST | 是 | 投票 |
| `/api/votes/history/` | GET | 是 | 投票记录 |

### 3.1 查询今日投票状态

- **URL**: `GET /api/votes/status/`
- **鉴权**: 需要

**成功响应 (200):**

```json
{
  "daily_limit": 3,
  "today_votes": 1,
  "remaining_votes": 2
}
```

### 3.2 投票

- **URL**: `POST /api/votes/cast/`
- **鉴权**: 需要

**请求体:**

```json
{
  "candidate_id": 1
}
```

**成功响应 (201):**

```json
{
  "message": "投票成功",
  "vote": {
    "id": 1,
    "candidate": 1,
    "candidate_name": "张三",
    "candidate_number": 1,
    "vote_date": "2026-07-09",
    "created_at": "2026-07-09 14:30:00"
  },
  "remaining_votes": 2
}
```

---

## 4. 礼物模块 `/api/gifts/`

| 接口 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/gifts/` | GET | 否 | 礼物列表 |
| `/api/gifts/send/` | POST | 是 | 赠送礼物 |
| `/api/gifts/history/` | GET | 是 | 赠送记录 |

### 4.1 赠送礼物

- **URL**: `POST /api/gifts/send/`
- **鉴权**: 需要

**请求体:**

```json
{
  "candidate_id": 1,
  "gift_id": 1,
  "quantity": 1
}
```

---

## 5. 支付模块 `/api/payments/`

| 接口 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/payments/recharge/` | POST | 是 | 创建充值订单 |
| `/api/payments/dev-pay/` | POST | 是 | 模拟支付（仅 DEBUG） |
| `/api/payments/orders/` | GET | 是 | 订单列表 |
| `/api/payments/wechat/notify/` | POST | 否 | 微信支付回调 |
| `/api/payments/alipay/notify/` | POST | 否 | 支付宝支付回调 |

### 5.1 创建充值订单

- **URL**: `POST /api/payments/recharge/`

**请求体:**

```json
{
  "amount": "100.00",
  "payment_method": "wechat"
}
```

`payment_method`: `wechat` | `alipay`

### 5.2 模拟支付（仅开发环境）

- **URL**: `POST /api/payments/dev-pay/`

**请求体:**

```json
{
  "order_no": "ORDABC123..."
}
```

---

## 6. 配置模块 `/api/config/`

| 接口 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/config/public/` | GET | 否 | 获取公开配置 |
| `/api/config/oss/sts/` | GET | 是 | 获取 OSS 上传 STS 临时凭证 |

### 6.1 获取公开配置

- **URL**: `GET /api/config/public/`
- **鉴权**: 不需要

**成功响应 (200):**

```json
{
  "daily_vote_limit": 3
}
```

---

### 6.2 获取 OSS 上传 STS 临时凭证

- **URL**: `GET /api/config/oss/sts/`
- **鉴权**: 需要（Bearer Token）

前端直传 OSS 前调用此接口，获取临时凭证后使用 [ali-oss](https://help.aliyun.com/document_detail/64041.html) 等 SDK 上传文件。

**成功响应 (200):**

```json
{
  "access_key_id": "STS.NUxxx",
  "access_key_secret": "xxx",
  "security_token": "CAISxxx",
  "expiration": "2026-07-13T15:00:00Z",
  "bucket": "aibaobendev",
  "endpoint": "oss-cn-hangzhou.aliyuncs.com",
  "region": "cn-hangzhou",
  "upload_dir": "uploads/12/",
  "base_url": "https://aibaobendev.oss-cn-hangzhou.aliyuncs.com"
}
```

| 字段 | 说明 |
|------|------|
| `access_key_id` / `access_key_secret` / `security_token` | STS 临时凭证三要素 |
| `expiration` | 凭证过期时间 |
| `bucket` / `endpoint` / `region` | OSS 连接信息 |
| `upload_dir` | 允许上传的目录前缀，文件 Key 须以此开头，如 `uploads/12/avatar.jpg` |
| `base_url` | 上传成功后的文件访问基础 URL，完整地址为 `{base_url}/{object_key}` |

**前端上传示例（ali-oss）:**

```javascript
// 1. 获取 STS 凭证
const sts = await fetch('/api/config/oss/sts/', {
  headers: { Authorization: `Bearer ${accessToken}` },
}).then(r => r.json());

// 2. 初始化 OSS 客户端并上传
const client = new OSS({
  region: sts.region,
  accessKeyId: sts.access_key_id,
  accessKeySecret: sts.access_key_secret,
  stsToken: sts.security_token,
  bucket: sts.bucket,
});
const objectKey = `${sts.upload_dir}avatar_${Date.now()}.jpg`;
const result = await client.put(objectKey, file);
const fileUrl = `${sts.base_url}/${objectKey}`;
```

> STS 凭证默认有效期 3600 秒，可在 `.env` 中通过 `OSS_STS_DURATION_SECONDS` 调整。凭证权限仅限当前用户目录下的上传与读取。

---

## 后台管理

访问 `http://localhost:8000/admin/` 管理所有数据表。修改 `daily_vote_limit` 配置项可调整每日投票上限。

### 报名审核

在后台「报名申请」中手动审核：

1. **列表批量通过**：勾选待审核记录 → 操作「通过选中的报名申请」
2. **详情页手动审核**：进入待审核申请详情 → 点击「通过审核」或「驳回此申请」
3. **通过**：自动创建候选人（默认参赛），立即展示在前端候选人列表和排行榜
4. **驳回**：填写驳回原因，用户收到反馈后可修改资料重新提交（头像/照片可不重新上传）

驳回原因会通过报名进度接口的 `status_message`、`reject_reason` 和 `resubmit_hint` 反馈给前端。

---

## 更新文档

同步 OpenAPI YAML（从代码注解自动生成）:

```bash
python manage.py generate_openapi
```

- 手写文档: `docs/API.md`
- OpenAPI 规范: `docs/openapi.yaml`
- 在线 Swagger: `http://localhost:8000/api/docs/`
- 在线 ReDoc: `http://localhost:8000/api/redoc/`
