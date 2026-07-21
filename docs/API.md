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

JSON 请求使用 `Content-Type: application/json`；报名提交支持 JSON（OSS 直传后传 `avatar_url` / `photos` URL 列表）或 `multipart/form-data`（头像可文件上传，`photos` 传 URL 的 JSON 字符串）。

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
| 礼物 | `/api/gifts/` | 礼物列表、按价格直付、余额赠送、赠送记录 |
| 支付/钱包 | `/api/payments/` | 余额、充值、提现、收款账户、订单、支付/提现回调 |
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

**限流响应 (429):** 同一手机号约 60 秒内不可重复发送（对齐阿里云分钟级流控）。

```json
{
  "detail": "发送过于频繁，请 45 秒后再试"
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
| `/api/candidates/` | GET | 否 | 候选人列表，支持按性别、报名类型、名称搜索筛选，以及按热度/票数排序 |
| `/api/candidates/{id}/` | GET | 否 | 候选人详情（含照片、团体成员、排名与距上一名票数差距） |
| `/api/candidates/ranking/` | GET | 否 | 排行榜，默认按热度；可改为按投票数，支持按性别、报名类型、名称搜索筛选 |

**候选人字段说明:**

| 字段 | 类型 | 说明 |
|------|------|------|
| `registration_type` | string | 报名类型：`individual`=个人，`group`=团体 |
| `registration_type_display` | string | 报名类型中文展示：个人 / 团体 |
| `gender` | string\|null | 性别：`male`=男，`female`=女；团体可为空 |
| `gender_display` | string | 性别中文展示：男 / 女 |
| `age` | integer\|null | 年龄；团体可为空 |
| `members` | array | 团体成员列表（`name`、`age`）；个人报名为空数组 |
| `vote_count` | integer | 投票数 |
| `heat_score` | integer | 热度值（投票 + 礼物转换） |
| `rank` | integer | 当前排名（与排行榜规则一致） |
| `votes_behind_previous` | integer\|null | 距上一名的票数差距；**第一名为 `null`**，前端可不展示 |

**排名规则**（列表/详情中的 `rank` 字段，以及排行榜默认排序）：`heat_score` 降序 → `vote_count` 降序 → `number` 升序。

**列表/排行榜筛选与排序参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `gender` | string | 否 | 按性别筛选，可选 `male`、`female` |
| `registration_type` | string | 否 | 按报名类型筛选，可选 `individual`、`group`；**不传则返回全部** |
| `name` | string | 否 | 按选手名称模糊搜索（个人姓名或团体名称，不区分大小写）；不传则不过滤 |
| `sort_by` | string | 否 | 排序方式：`heat_score`=按热度值降序，`vote_count`=按投票数降序。列表不传则按编号升序；排行榜不传则默认按热度值 |

**前端调用示例:**

- 按热度排行榜：`GET /api/candidates/ranking/` 或 `GET /api/candidates/ranking/?sort_by=heat_score`
- 按投票数排行榜：`GET /api/candidates/ranking/?sort_by=vote_count`
- 列表按热度排序（分页）：`GET /api/candidates/?sort_by=heat_score`
- 列表按投票数排序（分页）：`GET /api/candidates/?sort_by=vote_count`
- 按名称搜索：`GET /api/candidates/?name=张三`
- 排行榜按名称搜索：`GET /api/candidates/ranking/?name=舞团`

**列表响应示例:**

```json
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "name": "张三",
      "number": 1,
      "registration_type": "individual",
      "registration_type_display": "个人",
      "gender": "male",
      "gender_display": "男",
      "age": 22,
      "introduction": "热爱舞台",
      "avatar": "/media/candidates/avatars/xxx.jpg",
      "members": [],
      "vote_count": 10,
      "heat_score": 15,
      "rank": 2,
      "votes_behind_previous": 5,
      "is_active": true
    }
  ]
}
```

**详情响应示例**（`GET /api/candidates/{id}/`）：

```json
{
  "id": 2,
  "name": "李四",
  "number": 2,
  "registration_type": "individual",
  "registration_type_display": "个人",
  "gender": "female",
  "gender_display": "女",
  "age": 20,
  "introduction": "热爱舞台",
  "avatar": "/media/candidates/avatars/xxx.jpg",
  "vote_count": 80,
  "heat_score": 90,
  "rank": 2,
  "votes_behind_previous": 20,
  "is_active": true,
  "photos": [],
  "members": [],
  "created_at": "2026-07-13 10:00:00",
  "updated_at": "2026-07-16 14:00:00"
}
```

> 前端展示建议：当 `votes_behind_previous` 不为 `null` 时显示「距上一名还差 X 票」；为 `null`（第一名）时不显示。

**第一名详情示例**（`votes_behind_previous` 为 `null`）：

```json
{
  "id": 1,
  "name": "张三",
  "vote_count": 100,
  "heat_score": 120,
  "rank": 1,
  "votes_behind_previous": null
}
```

---

## 2.1 报名模块 `/api/candidates/applications/`

用户自主报名参加海选，提交后由后台审核。前端可通过「查询报名进度」接口获取审核状态与反馈文案。

| 接口 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/candidates/applications/submit/` | POST | 是 | 提交报名 / 修改个人资料 |
| `/api/candidates/applications/status/` | GET | 是 | 查询我的报名进度 |

### 2.1.1 提交报名 / 修改个人资料

- **URL**: `POST /api/candidates/applications/submit/`
- **鉴权**: 需要
- **Content-Type**: `multipart/form-data` 或 `application/json`

**请求字段:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `registration_type` | string | 是 | 报名类型：`individual`=个人，`group`=团体 |
| `name` | string | 是 | 个人姓名，或团体名称 |
| `gender` | string | 个人必填 | 性别：`male`=男，`female`=女；团体报名可不传 |
| `age` | integer | 个人必填 | 年龄，范围 1–120；团体报名可不传 |
| `members` | array | 团体必填 | 团体成员列表，每人含 `name`、`age`，**至少 3 人**；前端可按实际人数继续添加；个人报名勿传 |
| `introduction` | string | 否 | 个人/团体介绍 |
| `avatar` | file | 首次二选一 | 头像文件上传（与 `avatar_url` 二选一） |
| `avatar_url` | string | 首次二选一 | OSS 直传后的头像完整 URL，须在当前用户目录 `uploads/{user_id}/` 下 |
| `photos` | string[] | 否 | OSS 直传后的展示照片 URL 列表，最多 9 张；须在当前用户目录 `uploads/{user_id}/` 下；重新提交可不传，保留上次照片；multipart 时可传 JSON 字符串 |

**个人报名 JSON 示例:**

```json
{
  "registration_type": "individual",
  "name": "张三",
  "gender": "male",
  "age": 22,
  "introduction": "热爱舞台，期待展示自我",
  "avatar_url": "https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/12/avatar.jpg",
  "photos": [
    "https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/12/photo1.jpg",
    "https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/12/photo2.jpg"
  ]
}
```

**团体报名 JSON 示例:**

```json
{
  "registration_type": "group",
  "name": "青春舞团",
  "members": [
    {"name": "甲", "age": 20},
    {"name": "乙", "age": 21},
    {"name": "丙", "age": 22}
  ],
  "introduction": "三人街舞组合",
  "avatar_url": "https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/12/group.jpg",
  "photos": [
    "https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/12/g1.jpg"
  ]
}
```

**个人报名 multipart 示例:**

```
registration_type=individual
name=张三
gender=male
age=22
introduction=热爱舞台
avatar_url=https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/12/avatar.jpg
photos=["https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/12/photo1.jpg"]
```

**团体报名 multipart 示例（`members` 传 JSON 字符串）:**

```
registration_type=group
name=青春舞团
members=[{"name":"甲","age":20},{"name":"乙","age":21},{"name":"丙","age":22}]
introduction=三人街舞组合
avatar_url=https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/12/group.jpg
```

**成功响应 (201):**

```json
{
  "id": 1,
  "registration_type": "individual",
  "registration_type_display": "个人",
  "name": "张三",
  "gender": "male",
  "gender_display": "男",
  "age": 22,
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
  "members": [],
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
- 个人报名须填写姓名、性别、年龄；团体报名须填写团体名称，以及至少 3 名成员的姓名和年龄
- 用户可随时修改资料，每次提交后均需后台重新审核
- 首次审核通过后自动创建候选人（团体创建 1 个候选人并同步成员列表）；后续资料修改审核通过后更新已有候选人信息
- 审核期间及驳回后，候选人列表仍展示上次已通过的资料
- 被驳回后可修改资料重新提交；头像和照片可不传，将保留上次内容

**重新提交请求示例:**

```
registration_type=individual
name=李四
gender=female
age=23
introduction=更新后的个人介绍
```

**已成为候选人后修改资料示例:**

```
registration_type=individual
name=李四
gender=female
age=23
introduction=更新后的个人介绍
avatar_url=https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/12/new_avatar.jpg
```

**错误响应 (400):**

```json
{
  "detail": "您已有待审核的资料修改，请耐心等待审核结果"
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
    "registration_type": "individual",
    "registration_type_display": "个人",
    "name": "张三",
    "gender": "male",
    "gender_display": "男",
    "age": 22,
    "introduction": "热爱舞台，期待展示自我",
    "avatar": "/media/applications/avatars/xxx.jpg",
    "photos": [],
    "members": [],
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

**审核通过时** `status` 为 `approved`，`is_candidate` 为 `true`，`can_apply` 和 `can_resubmit` 为 `true`，个人报名 `resubmit_hint` 为 `"可修改姓名、性别、年龄、介绍、头像或照片，提交后需后台重新审核"`，团体报名对应为修改团体名称与成员信息，`candidate_id` 返回关联的候选人 ID，该候选人会出现在 `/api/candidates/` 列表和排行榜中。

**审核驳回时** `status` 为 `rejected`，`can_apply` 和 `can_resubmit` 为 `true`。若用户此前已是候选人，`is_candidate` 仍为 `true`，候选人列表继续展示上次已通过的资料。`resubmit_hint` 会提示修改对应类型的资料，`status_message` 包含驳回原因。

**审核驳回响应示例:**

```json
{
  "has_application": true,
  "can_apply": true,
  "can_resubmit": true,
  "is_candidate": false,
  "resubmit_hint": "资料被驳回，请修改姓名、性别、年龄、介绍或照片后重新提交",
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
  "can_apply": true,
  "can_resubmit": true,
  "is_candidate": true,
  "resubmit_hint": "可修改姓名、性别、年龄、介绍、头像或照片，提交后需后台重新审核",
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
| `pending` | 待审核 | 已提交或修改资料，等待后台审核 |
| `approved` | 已通过 | 审核通过；已成为候选人，可继续修改资料 |
| `rejected` | 已驳回 | 审核未通过，可修改后重新提交 |

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

均返回 **HTTP 200**，用 `success` 判断是否投票成功。

**投票成功:**

```json
{
  "success": true,
  "message": "投票成功",
  "vote": {
    "id": 1,
    "candidate": 1,
    "candidate_name": "张三",
    "candidate_number": 1,
    "vote_date": "2026-07-09",
    "created_at": "2026-07-09 14:30:00"
  },
  "remaining_votes": 2,
  "daily_limit": 3,
  "today_votes": 1
}
```

**今日次数已用完:**

```json
{
  "success": false,
  "message": "今日投票次数已用完（每日限3票）",
  "vote": null,
  "remaining_votes": 0,
  "daily_limit": 3,
  "today_votes": 3
}
```

候选人不存在或已下架时仍返回 **400** `{"detail":"..."}`。

---

## 4. 礼物模块 `/api/gifts/`

| 接口 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/gifts/` | GET | 否 | 礼物列表（含单价 `price`） |
| `/api/gifts/pay/` | POST | 是 | **按礼物价格直接发起微信/支付宝支付** |
| `/api/gifts/send/` | POST | 是 | 余额赠送礼物 |
| `/api/gifts/history/` | GET | 是 | 赠送记录 |

### 4.1 按礼物价格发起支付（推荐）

根据礼物单价自动计算应付金额（`单价 × 数量`），创建微信/支付宝订单。前端**不必传金额**。

- **URL**: `POST /api/gifts/pay/`
- **鉴权**: 需要

**请求体（Native 扫码，默认）:**

```json
{
  "candidate_id": 1,
  "gift_id": 1,
  "quantity": 2,
  "payment_method": "wechat",
  "payment_mode": "native"
}
```

**请求体（微信 JSAPI，微信内支付）:**

```json
{
  "candidate_id": 1,
  "gift_id": 1,
  "quantity": 2,
  "payment_method": "wechat",
  "payment_mode": "jsapi",
  "openid": "用户在商户AppID下的openid"
}
```

**请求体（支付宝 H5 手机网站支付）:**

```json
{
  "candidate_id": 1,
  "gift_id": 1,
  "quantity": 2,
  "payment_method": "alipay",
  "payment_mode": "h5"
}
```

| 字段 | 说明 |
|------|------|
| `candidate_id` | 候选人 ID |
| `gift_id` | 礼物 ID（价格从礼物表读取） |
| `quantity` | 数量，默认 1 |
| `payment_method` | `wechat` \| `alipay` |
| `payment_mode` | `native`（默认扫码）\| `jsapi`（仅微信；需 `openid`）\| `h5`（仅支付宝手机网站） |
| `openid` | 微信用户 openid；`jsapi` 时必填 |

**成功响应 Native (201):**

```json
{
  "message": "请完成支付，支付成功后礼物将自动赠送",
  "gift": {
    "id": 1,
    "name": "玫瑰",
    "unit_price": "9.90",
    "heat_value": 10,
    "quantity": 2,
    "total_amount": "19.80",
    "total_heat": 20
  },
  "payment_method": "wechat",
  "order": {
    "order_no": "GFXXXXXXXX",
    "order_type": "gift",
    "payment_method": "wechat",
    "amount": "19.80",
    "status": "pending",
    "extra_data": {
      "candidate_id": 1,
      "gift_id": 1,
      "quantity": 2,
      "gift_name": "玫瑰",
      "candidate_name": "候选人A"
    },
    "paid_at": null,
    "created_at": "2026-07-15T10:00:00Z"
  },
  "pay_data": {
    "order_no": "GFXXXXXXXX",
    "payment_mode": "native",
    "code_url": "weixin://wxpay/bizpayurl?pr=xxxx",
    "qr_code": "weixin://wxpay/bizpayurl?pr=xxxx",
    "expires_at": "2026-07-15T10:02:00+08:00"
  }
}
```

**成功响应 JSAPI 时 `pay_data`:**

```json
{
  "order_no": "GFXXXXXXXX",
  "payment_mode": "jsapi",
  "jsapi_params": {
    "appId": "wx...",
    "timeStamp": "1710000000",
    "nonceStr": "abc123",
    "package": "prepay_id=wx...",
    "signType": "RSA",
    "paySign": "..."
  },
  "expires_at": "2026-07-15T10:02:00+08:00"
}
```

**成功响应支付宝 H5 时 `pay_data`:**

```json
{
  "order_no": "GFXXXXXXXX",
  "payment_mode": "h5",
  "pay_url": "https://openapi.alipay.com/gateway.do?...",
  "payment_link_url": "https://openapi.alipay.com/gateway.do?...",
  "expires_at": "2026-07-15T10:02:00+08:00"
}
```

前端拿到 `pay_url` 后直接跳转：`window.location.href = pay_data.pay_url`。支付完成会异步回调，也可轮询订单状态；若配置了 `ALIPAY_RETURN_URL`，用户支付后会同步跳回该页。
**前端流程:**

1. `GET /api/gifts/` 展示礼物及 `price`
2. 用户选择礼物与数量 → `POST /api/gifts/pay/`
3. Native：用 `pay_data.code_url` / `qr_code` 生成二维码，微信「扫一扫」付款  
   JSAPI：在微信内用 `pay_data.jsapi_params` 调起 `WeixinJSBridge.invoke('getBrandWCPayRequest', ...)`
4. 轮询 `GET /api/payments/orders/{order_no}/`，`status=paid` 即支付成功并已自动赠送

本地未配支付时可对返回的 `order_no` 调 `POST /api/payments/dev-pay/` 模拟成功。

### 4.2 余额赠送礼物

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

**成功响应 (201):**

```json
{
  "message": "礼物赠送成功",
  "payment_method": "balance",
  "transaction": {
    "id": 1,
    "gift": 1,
    "gift_name": "玫瑰",
    "candidate": 1,
    "candidate_name": "候选人A",
    "quantity": 1,
    "total_price": "9.90",
    "total_heat": 10,
    "created_at": "2026-07-15T10:00:00Z"
  },
  "balance": "90.10"
}
```

---

## 5. 支付/钱包模块 `/api/payments/`

| 接口 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/payments/wallet/` | GET | 是 | 查询余额 |
| `/api/payments/recharge/` | POST | 是 | 创建充值订单（微信/支付宝扫码） |
| `/api/payments/dev-pay/` | POST | 是 | 模拟支付（仅 DEBUG） |
| `/api/payments/orders/` | GET | 是 | 支付订单列表 |
| `/api/payments/orders/{order_no}/` | GET | 是 | 查询单笔订单状态 |
| `/api/payments/payee-accounts/` | GET | 是 | 收款账户列表 |
| `/api/payments/payee-accounts/` | POST | 是 | 绑定收款账户 |
| `/api/payments/payee-accounts/` | DELETE | 是 | 解绑收款账户 |
| `/api/payments/withdraw/` | POST | 是 | 申请提现 |
| `/api/payments/withdraws/` | GET | 是 | 提现记录 |
| `/api/payments/wechat/notify/` | POST | 否 | 微信支付结果回调 |
| `/api/payments/alipay/notify/` | POST | 否 | 支付宝支付结果回调 |
| `/api/payments/withdraw/wechat/notify/` | POST | 否 | 微信提现结果回调 |
| `/api/payments/withdraw/alipay/notify/` | POST | 否 | 支付宝提现结果回调 |

> 支付回调 URL 须配置为公网 HTTPS，并在商户平台填写一致。本地开发可用 `dev-pay` 模拟入账。

### 5.1 查询余额

- **URL**: `GET /api/payments/wallet/`

```json
{ "balance": "100.00" }
```

### 5.2 创建充值订单

- **URL**: `POST /api/payments/recharge/`

**请求体（Native 扫码，默认）:**

```json
{
  "amount": "100.00",
  "payment_method": "wechat",
  "payment_mode": "native"
}
```

**请求体（微信 JSAPI）:**

```json
{
  "amount": "100.00",
  "payment_method": "wechat",
  "payment_mode": "jsapi",
  "openid": "用户在商户AppID下的openid"
}
```

**请求体（支付宝 H5）:**

```json
{
  "amount": "100.00",
  "payment_method": "alipay",
  "payment_mode": "h5"
}
```

| 字段 | 说明 |
|------|------|
| `payment_method` | `wechat` \| `alipay` |
| `payment_mode` | `native`（默认）\| `jsapi`（仅微信；需 `openid`）\| `h5`（仅支付宝） |
| `openid` | 微信用户 openid；`jsapi` 时必填 |

**成功响应 Native (201):**

```json
{
  "order": {
    "order_no": "RCXXXXXXXX",
    "order_type": "recharge",
    "payment_method": "wechat",
    "amount": "100.00",
    "status": "pending",
    "extra_data": {},
    "paid_at": null,
    "created_at": "2026-07-15T10:00:00Z"
  },
  "pay_data": {
    "order_no": "RCXXXXXXXX",
    "payment_mode": "native",
    "code_url": "weixin://wxpay/bizpayurl?pr=xxxx",
    "qr_code": "weixin://wxpay/bizpayurl?pr=xxxx",
    "expires_at": "2026-07-15T10:02:00+08:00"
  }
}
```

**成功响应 JSAPI 时 `pay_data`:**

```json
{
  "order_no": "RCXXXXXXXX",
  "payment_mode": "jsapi",
  "jsapi_params": {
    "appId": "wx...",
    "timeStamp": "1710000000",
    "nonceStr": "abc123",
    "package": "prepay_id=wx...",
    "signType": "RSA",
    "paySign": "..."
  },
  "expires_at": "2026-07-15T10:02:00+08:00"
}
```

支付成功后回调入账，余额增加。可用订单详情接口轮询 `status=paid`。

也可用专用入口：`POST /api/payments/recharge/jsapi/`（强制 JSAPI；body 传 `amount` + `openid`，未传 openid 时尝试用已绑定微信收款账号）。

### 5.3 模拟支付（仅开发环境）

- **URL**: `POST /api/payments/dev-pay/`
- **条件**: `DEBUG=True`

**请求体:**

```json
{
  "order_no": "RCXXXXXXXX"
}
```

成功后返回更新后的 `order` 与 `balance`。对礼物订单会同时完成赠送。

### 5.4 订单列表 / 详情

- `GET /api/payments/orders/`
- `GET /api/payments/orders/{order_no}/` → `{ "order": {...}, "balance": "..." }`

订单 `status`: `pending` | `paid` | `failed` | `cancelled` | `refunded`  
订单 `order_type`: `recharge` | `gift`

### 5.5 收款账户（提现收款方）

#### 列表

- **URL**: `GET /api/payments/payee-accounts/`

```json
{
  "accounts": [
    {
      "channel": "alipay",
      "account": "138****8000",
      "account_name": "张三",
      "updated_at": "2026-07-15T10:00:00Z"
    }
  ]
}
```

#### 绑定

- **URL**: `POST /api/payments/payee-accounts/`

```json
{
  "channel": "wechat",
  "account": "用户openid",
  "account_name": "张三"
}
```

| channel | account 含义 |
|---------|----------------|
| `wechat` | 用户在该商户 AppID 下的 **openid** |
| `alipay` | 支付宝登录号（手机号或邮箱） |

每个用户每个渠道仅保留一份绑定，重复绑定会覆盖。

#### 解绑

- **URL**: `DELETE /api/payments/payee-accounts/`

```json
{ "channel": "wechat" }
```

### 5.6 申请提现

- **URL**: `POST /api/payments/withdraw/`

**前置**: 已绑定对应渠道收款账户；余额充足。

```json
{
  "amount": "50.00",
  "channel": "alipay"
}
```

**成功响应 (201):**

```json
{
  "message": "提现已受理",
  "order": {
    "order_no": "WDXXXXXXXX",
    "channel": "alipay",
    "amount": "50.00",
    "status": "pending",
    "payee_account": "138****8000",
    "payee_name": "张三",
    "provider_trade_no": "...",
    "remark": "",
    "completed_at": null,
    "created_at": "2026-07-15T10:00:00Z"
  },
  "balance": "50.00"
}
```

提现状态 `status`:

| 值 | 说明 |
|----|------|
| `pending` | 处理中（等待通道回调） |
| `await_confirm` | 微信待用户确认收款 |
| `success` | 成功 |
| `failed` | 失败（余额已自动退回） |
| `cancelled` | 已取消 |

微信新版商家转账若需用户确认，响应会额外返回：

```json
{
  "message": "提现待用户在微信侧确认收款",
  "wechat_confirm": {
    "mchId": "1110450807",
    "appId": "wx...",
    "packageInfo": "...",
    "transferState": "WAIT_USER_CONFIRM",
    "needUserConfirm": true
  }
}
```

前端使用微信「确认收款」组件，传入 `packageInfo`。

### 5.7 提现记录

- **URL**: `GET /api/payments/withdraws/`

### 5.8 支付 / 提现回调（服务端，勿由前端调用）

| URL | 通道 | 作用 |
|-----|------|------|
| `POST /api/payments/wechat/notify/` | 微信 APIv3 | 充值/礼物支付成功 → 入账或发礼物 |
| `POST /api/payments/alipay/notify/` | 支付宝 | 同上 |
| `POST /api/payments/withdraw/wechat/notify/` | 微信商家转账 | 提现成功/失败 |
| `POST /api/payments/withdraw/alipay/notify/` | 支付宝转账 | 提现结果（若配置） |

微信回调：验签 + AEAD 解密后更新订单；响应 `{"code":"SUCCESS","message":"成功"}`。  
支付宝回调：RSA2 验签；响应纯文本 `success` / `fail`。

`.env` 关键注意：

- `WECHAT_PAY_PLATFORM_SERIAL_NO` 必须是商户平台「微信支付公钥」的 **公钥 ID**（如 `PUB_KEY_ID_xxx`），**不是** pem 文件路径；微信提现必填。
- 密钥/证书路径可写项目相对路径，如 `secrets/apiclient_key.pem`。

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
