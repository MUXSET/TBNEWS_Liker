# E+ 新闻点赞工具 — API 与认证参考文档

> 最后更新: 2026-03-10 | 作者: MUXSET

---

## 1. 认证体系总览

本项目涉及**两套独立的认证体系**，分别服务于不同的 API 域：

| 认证体系 | 域名 | 凭据类型 | 获取方式 | 用途 |
|---------|------|---------|---------|------|
| **tbeanews Token** | `tbeanews.tbea.com` | HTTP Header `token` | Playwright 自动登录后从 Cookie `tbea_art_token` 提取 | 文章详情查询、点赞 |
| **ejia Session Cookies** | `ejia.tbea.com` | 浏览器 Cookies | Playwright 登录 `ejia.tbea.com` 后用 `context.cookies()` 提取 | IM 消息 API、Session 保活 |

> [!WARNING]
> Cookie 中的 `cu` 字段（如 `64adb51ebd8cca024593457e`）**不等于** IM `groupId` 中的 userId（如 `64adb51fbd8cca02459346eb`）！构建 `groupId` 时必须使用 IM 专用 userId。

---

## 2. 登录入口

```
URL:  https://ejia.tbea.com/
方式: Playwright 无头浏览器模拟
```

**登录流程（对应 `get_token.py`）：**
1. 打开 `https://ejia.tbea.com/`
2. 点击 `.user-name` 切换到账号密码模式
3. 填写 `#email`（工号）和 `#password`
4. 点击 `#log-btn` 提交
5. 等待跳转到 `yzj-layout/home/`（首页 Portal）
6. 在首页 `iframe[src*='portal']` 中，定位新闻资讯卡片 `div.card-component:has(span[title='新闻资讯'])`
7. 点击卡片右上角 `.card-header-button`（"更多"按钮），会打开新标签页 → `tbeanews.tbea.com`
8. 在新标签页中，点击第一篇文章 `(//li[@class='article-item'])[1]`
9. 等待 `networkidle`，此时浏览器会设置 Cookie `tbea_art_token`
10. 调用 `context.cookies()` 提取全部 Cookies：
    - `tbea_art_token` → 存为 tbeanews Token
    - 其余 ejia Cookies（见第 5 节）→ 存为 IM 会话凭据

---

## 3. tbeanews 新闻 API

### 3.1 文章详情

```http
GET https://tbeanews.tbea.com/api/article/detail?id={article_id}
```

| 参数 | 位置 | 说明 |
|-----|------|------|
| `id` | Query | 文章数字 ID（如 `11995`） |
| `token` | Header | tbea_art_token 值 |

**响应示例：**
```json
{
  "code": 1,
  "data": {
    "id": 11995,
    "title": "护航绿电！...",
    "is_digg": false,
    "pid": "XT-2bb8a866-..."
  }
}
```

| 字段 | 说明 |
|-----|------|
| `code` | `1` = 成功 |
| `is_digg` | `true` = 已点赞，`false` = 未点赞 |
| `pid` | 发布账号 ID（⚠️ 不能用于判断推送频道） |

---

### 3.2 文章点赞

```http
POST https://tbeanews.tbea.com/api/article/addDigg
Content-Type: application/json
```

| 参数 | 位置 | 说明 |
|-----|------|------|
| `token` | Header | tbea_art_token 值 |
| `id` | Body (JSON) | 文章 ID（字符串格式） |

**请求体：**
```json
{ "id": "11995" }
```

**响应：**
```json
{ "code": 1, "msg": "点赞成功" }
```

重复点赞时 `msg` 会包含 `"重复点赞"`，均视为成功。

---

### 3.3 文章列表（备用）

```http
GET https://tbeanews.tbea.com/api/article/lists?page={page}&limit={limit}
```

> 此接口**无法按频道过滤**，仅用于顺序扫描。月度补漏使用 IM 消息 API 代替。

---

## 4. ejia IM 消息 API（核心）

### 4.1 获取频道消息列表

```http
POST https://ejia.tbea.com/im/rest/message/listMessage
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
```

| 参数 | 值 | 说明 |
|-----|-----|------|
| `groupId` | `XT-{userId}-{channelId}` | 拼接而成 |
| `userId` | 留空 | 不需要填 |
| `type` | `new` / `old` | 首页用 `new`，翻页用 `old` |
| `count` | `10` ~ `20` | 每页条数 |
| `msgId` | 留空 / 上页末尾 msgId | 分页游标 |

**必需 Cookies：** ejia Session Cookies（见下方第 5 节）

**必需 Headers：**
```
X-Requested-With: XMLHttpRequest
Origin: https://ejia.tbea.com
Referer: https://ejia.tbea.com/im/xiaoxi/
```

**响应示例：**
```json
{
  "data": {
    "list": [
      {
        "msgType": 6,
        "sendTime": "2026-03-06 18:30:00",
        "msgId": "abc123...",
        "param": {
          "list": [
            {
              "title": "护航绿电！...",
              "url": "https://...?id=11995"
            }
          ]
        }
      }
    ],
    "more": true
  },
  "success": true
}
```

| 字段 | 说明 |
|-----|------|
| `msgType` | `6` = 图文新闻推送（只关心这个类型） |
| `sendTime` | 推送时间，格式 `YYYY-MM-DD HH:MM:SS`，用于按月筛选 |
| `param.list[]` | 多图文模式，每条含 `title` 和 `url`（内含文章 ID） |
| `param.url` | 单图文模式的文章链接 |
| `more` | `true` = 还有更多历史消息可翻页 |

**从消息中提取文章 ID：**
```
URL 格式: https://tbeanews.tbea.com/...?id=11995&...
提取正则: re.search(r'id=(\d+)', url)
```
- 多图文：遍历 `param.list[]` 中每条的 `url`
- 单图文：直接取 `param.url`

---

### 4.2 分页逻辑

```
第 1 页: type=new, msgId=（空）
第 N 页: type=old, msgId=（上一页最后一条的 msgId）
终止条件: more=false 或 sendTime 已早于目标月份
```

---

## 5. Session Cookies 清单

Playwright 登录后需提取的关键 Cookies：

| Cookie 名 | 示例值 | 必需 | 说明 |
|-----------|-------|------|------|
| `JSESSIONID` | `lpymyqtix6aaw...` | ⚠️ | IM 服务会话 ID |
| `at` | `a7ff36d5-5fae-...` | ✅ | 认证令牌 |
| `webLappToken` | `RTXcirUwxXc...` | ✅ | Web 应用令牌 |
| `cu` | `64adb51ebd...` | ✅ | 用户标识（⚠️ 非 IM userId） |
| `sync_userid` | `64adb51ebd...` | ✅ | 同步用户 ID |
| `sync_networkid` | `101` | ✅ | 网络 ID |
| `cn` | `101` | ✅ | 公司网络 |
| `cd` | `ejia.tbea.com` | ✅ | 域标识 |
| `uuid` | `1fd4f4fa-...` | ✅ | 会话唯一标识 |
| `gl` | `04e9c284-...` | ✅ | 全局会话 |
| `__loginType` | `2` | ✅ | 登录方式 |
| `toweibologin` | `login` | ✅ | 登录标识 |
| `ERPPRD` | `pTT1o0yx...` | ⚠️ | ERP 会话（Playwright 可能不捕获） |
| `redirectIndexUrl` | `/yzj-layout/home` | ❌ | 重定向（非必需） |

---

## 6. Session 保活

```http
POST https://ejia.tbea.com/space/c/rest/user/checkLogin
Content-Length: 0
```

| Header | 值 |
|--------|-----|
| `X-Requested-With` | `XMLHttpRequest` |
| `X-Yzj-Lang` | `zh-CN` |
| `X-Yzj-Payload` | `e:101;u:{cu_value}` |

- **频率**: 每 5 分钟自动调用
- **作用**: 防止 ejia Session 过期
- **用法**: 在自动挂机模式下由 `TaskManager` 调度

---

## 7. 目标频道配置

| 频道名称 | Channel ID | 用途 |
|---------|------------|------|
| 特变电工股份有限公司 | `XT-2bb8a866-d2a3-47da-bbad-8c63db21e9b6` | 集团新闻 |
| 新变厂新闻资讯 | `XT-0ba2025b-e2cb-498b-99b1-cdc741a21f75` | 新变厂新闻 |
| 开讲了 | `XT-1b1e03a9-8222-4b7f-a7eb-a5d91e2d012d` | 学习专栏 |

**GroupId 构造公式：**
```
XT-{IM专用userId}-{channelId}
```

> IM 专用 userId（`64adb51fbd8cca02459346eb`）存储在 `config.json` 的 `ejia_user_id` 字段。

---

## 8. config.json 完整结构

```json
{
    "username": "178145",
    "password": "178145",
    "tbea_art_token": "28aa3c10e056...",
    "scan_interval_hours": 1.0,
    "token_refresh_interval_hours": 6.0,
    "ejia_cookies": {
        "JSESSIONID": "...",
        "at": "...",
        "webLappToken": "...",
        "...": "其他 cookies"
    },
    "ejia_user_id": "64adb51fbd8cca02459346eb"
}
```

| 字段 | 刷新时机 |
|-----|---------|
| `tbea_art_token` | 每次 Playwright 登录（约 6h 一次） |
| `ejia_cookies` | 每次 Playwright 登录自动更新 |
| `ejia_user_id` | 首次设置后不再覆盖（手动管理） |

---

## 9. 关键发现与踩坑记录

1. **`pid` ≠ 推送频道**：文章的 `pid` 字段代表制作方，不代表是哪个频道推送的。只有 IM 消息 API 能确定频道归属。
2. **`cu` ≠ IM userId**：Cookie 中的 `cu` 值和 IM `groupId` 中的 userId 有多个字符不同，必须从 IM 页面的 `data-groupid` 属性提取正确值。
3. **双 Session 架构**：`ejia.tbea.com`（IM）和 `tbeanews.tbea.com`（新闻）使用不同的认证体系，必须用两个独立的 `requests.Session` 分别请求，否则 Cookies 会互相干扰。
4. **IM 页面无法直接访问**：Headless 浏览器访问 `/im/xiaoxi/` 会被重定向到 `/yzj-layout/home/`，IM 模块是嵌入在主页里的 SPA 组件。
