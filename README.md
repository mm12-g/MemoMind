# MemoMind · AI 温柔记忆

> 一款基于 FSRS 智能间隔重复算法和 AI 大模型的全栈记忆助手，治愈系玻璃卡片 UI，让记忆变得温柔而科学 🌸

<div align="center">

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)
![Vue](https://img.shields.io/badge/Vue-3.5-42b883.svg)
![Vite](https://img.shields.io/badge/Vite-6.0-646cff.svg)
![FSRS](https://img.shields.io/badge/FSRS-6.3.2-ff6b9d.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-003087.svg)
![Element Plus](https://img.shields.io/badge/Element_Plus-2.8-409EFF.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

</div>

---

## ✨ 核心特性

- 🧠 **FSRS 6.3.2 智能间隔重复** — 基于 DSR（Difficulty, Stability, Retrievability）三参数动态调度复习，科学记忆曲线
- 🤖 **AI 自动生成卡片** — 上传 PDF/DOCX/TXT/MD 文档或粘贴文本，一键生成结构化复习卡片
- 📝 **4 种卡片类型** — 基础问答 / 面试题 / 选择题 / 英语单词，动态表单 + 针对性复习
- 📚 **知识库 + 标签 + 联想记忆** — 多级组织知识，卡片间可建立前置/相似/对比关系
- 🎤 **费曼学习法** — 假装讲给小白听，AI 三维度评分（流畅度 / 简单度 / 准确度）定位卡壳点
- 🎯 **专项训练** — 面试模拟 / 模拟考试 / 英语单词三种训练模式
- 📊 **学习分析仪表盘** — 复习趋势、正确率、保持率预估、薄弱知识点自动发现
- 🔁 **错题本批量重练** — 一键把最近 Again 过的卡片集中复习
- 💫 **治愈系玻璃卡片 UI** — 柔和玫瑰 / 蜜桃 / 薄荷 / 木色配色，backdrop-blur 毛玻璃效果

---

## 🏗️ 技术栈

### 后端

| 技术 | 版本 | 用途 |
|---|---|---|
| Python | 3.12+ | 运行时 |
| FastAPI | 0.115 | Web 框架 |
| SQLAlchemy | 2.0 | ORM（同步模式） |
| Alembic | 1.14 | 数据库迁移 |
| PostgreSQL / SQLite | — | 数据库（开发用 SQLite，生产用 PostgreSQL） |
| FSRS | 6.3.2 | 间隔重复算法 |
| python-jose + bcrypt | — | JWT 认证 + 密码哈希 |
| PyMuPDF / python-docx | — | PDF/DOCX 文档解析 |
| DeepSeek API | — | AI 卡片生成 + 答案评分 |
| Pytest | 8.3 | 单元测试（14 tests 全绿） |

### 前端

| 技术 | 版本 | 用途 |
|---|---|---|
| Vue | 3.5 | SPA 框架 |
| TypeScript | 5.6 | 类型安全 |
| Vite | 6.0 | 构建工具 |
| Pinia | 2.2 | 状态管理 |
| Element Plus | 2.8 | 组件库 |
| ECharts | 5 | 数据可视化 |
| Vue Router | 4 | 路由 |

---

## 📁 项目结构

```
MemoMind/
├── backend/                          # FastAPI 后端
│   ├── app/
│   │   ├── ai/                       # AI Provider 封装
│   │   │   ├── deepseek.py
│   │   │   ├── prompts.py
│   │   │   └── provider.py
│   │   ├── api/v1/                   # REST API 路由（12 个文件）
│   │   │   ├── auth.py               #   注册 / 登录 / 用户信息
│   │   │   ├── decks.py              #   知识库 CRUD
│   │   │   ├── cards.py              #   卡片 CRUD + 批量导入 + 批量删除
│   │   │   ├── tags.py               #   标签管理
│   │   │   ├── reviews.py            #   FSRS 复习会话 / 提交 / 日志
│   │   │   ├── ai.py                 #   AI 任务（文档解析 / 卡片生成 / 评分）
│   │   │   ├── analytics.py          #   保持率预估
│   │   │   ├── goals.py              #   每日目标
│   │   │   ├── practice.py           #   专项训练 + 错题本
│   │   │   └── router.py             #   统一注册
│   │   ├── core/                     # 核心配置
│   │   │   ├── config.py             #   Pydantic Settings（.env 加载）
│   │   │   ├── database.py           #   SQLAlchemy Engine + SessionLocal
│   │   │   ├── security.py           #   JWT 签发 / bcrypt 哈希
│   │   │   ├── deps.py               #   get_current_user Depends
│   │   │   └── exceptions.py         #   统一异常处理
│   │   ├── models/                   # SQLAlchemy ORM（11 个模型）
│   │   ├── schemas/                  # Pydantic 请求/响应模型
│   │   ├── services/                 # 业务逻辑层
│   │   │   ├── fsrs_service.py       #   FSRS 调度封装
│   │   │   ├── analytics_service.py  #   Dashboard / Statistics / Retention
│   │   │   ├── ai_service.py         #   AI 卡片生成 / 评分
│   │   │   ├── feynman_service.py    #   费曼 AI 评估
│   │   │   ├── document_parser.py    #   PDF/DOCX 解析
│   │   │   └── associate_service.py  #   联想记忆（卡片关联）
│   │   ├── main.py
│   │   └── uploads/                  # 用户上传文件（.gitignore）
│   ├── alembic/                      # 数据库迁移（6 个版本）
│   ├── tests/                        # Pytest 单元测试
│   │   ├── conftest.py               #   StaticPool 内存 SQLite fixture
│   │   ├── test_auth.py               #   5 tests
│   │   ├── test_fsrs.py               #   3 tests
│   │   └── test_analytics.py          #   6 tests
│   ├── alembic.ini
│   └── requirements.txt
│
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── api/                      # axios 封装（12 个模块）
│   │   ├── stores/                   # Pinia（user store）
│   │   ├── views/                    # 页面组件
│   │   │   ├── Login.vue
│   │   │   ├── Register.vue
│   │   │   ├── Dashboard.vue         #   首页仪表盘
│   │   │   ├── Review.vue            #   FSRS 复习页
│   │   │   ├── AIStudio.vue          #   AI 工作台
│   │   │   ├── FeynmanMode.vue       #   费曼学习
│   │   │   ├── Analytics.vue         #   学习分析
│   │   │   ├── Planner.vue           #   学习计划
│   │   │   ├── Tags.vue              #   标签管理
│   │   │   ├── Settings.vue          #   个人设置
│   │   │   ├── decks/                #   知识库列表 / 详情
│   │   │   ├── cards/                #   卡片表单
│   │   │   └── practice/             #   面试 / 考试 / 英语专项
│   │   ├── layouts/MainLayout.vue    #   主布局（侧边栏 + 顶部）
│   │   ├── router/index.ts           #   路由守卫（JWT）
│   │   ├── style.css                 #   全局治愈系样式
│   │   └── main.ts
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── .env.example
├── .gitignore
└── PROJECT_PLAN.md
```

---

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- npm / pnpm / yarn

### 1. 克隆仓库

```bash
git clone https://github.com/mm12-g/MemoMind.git
cd MemoMind
```

### 2. 后端启动

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # Linux / macOS

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env，填写 DEEPSEEK_API_KEY

# 数据库迁移
alembic upgrade head

# 启动服务（开发模式 + 热重载）
uvicorn app.main:app --reload --port 8000
```

后端启动后访问：
- API 文档（Swagger UI）：http://127.0.0.1:8000/docs
- API 文档（ReDoc）：http://127.0.0.1:8000/redoc

### 3. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

浏览器打开 http://localhost:5173 即可访问。

### 4. 运行后端测试

```bash
cd backend
pytest tests/ -v
# 期望输出：14 passed, 4 warnings in 3.xx s
```

---

## 🔐 环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DATABASE_URL` | 数据库连接串 | `sqlite:///./memomind.db` |
| `JWT_SECRET_KEY` | JWT 签名密钥（**生产必须修改**） | `dev-secret-change-me` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 有效期（分钟） | `1440`（24 小时） |
| `DEEPSEEK_API_KEY` | DeepSeek AI 密钥（卡片生成 / 评分） | — |
| `DEEPSEEK_MODEL` | 使用的模型 | `deepseek-chat` |
| `DEEPSEEK_BASE_URL` | API Base URL | `https://api.deepseek.com` |

生产环境推荐 PostgreSQL：
```
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/memomind
```

---

## 🧩 API 概览

所有 API 统一返回 `{ code, message, data }` 格式，非公开端点需 `Authorization: Bearer <token>`。

| 模块 | 端点 | 说明 |
|---|---|---|
| **Auth** | `POST /auth/register` | 注册新用户 |
| | `POST /auth/login` | 邮箱 + 密码登录，返回 access_token |
| | `GET /auth/me` | 获取当前用户信息 |
| **知识库** | `GET /decks` | 用户的知识库列表 |
| | `POST /decks` | 新建知识库 |
| | `GET /decks/{id}` | 知识库详情（含卡片统计） |
| | `PUT /decks/{id}` / `DELETE /decks/{id}` | 修改 / 删除 |
| **卡片** | `GET /cards` | 卡片列表（支持 deck_id / card_type / keyword 筛选） |
| | `POST /cards` | 新建卡片（4 种类型动态表单） |
| | `DELETE /cards/{id}` | 删除单张 |
| | `DELETE /cards/batch` | 批量删除（`{ card_ids: [...] }`） |
| | `POST /cards/import` | 批量 JSON 导入 |
| **标签** | `GET /tags` / `POST /tags` | 列表 / 创建 |
| | `PUT /tags/{id}` / `DELETE /tags/{id}` | 修改 / 删除 |
| **复习** | `POST /reviews/start` | 开始复习会话（支持 `card_id` / `card_ids` / `mistake_only`） |
| | `POST /reviews/submit/{card_id}` | 提交复习结果（自动 FSRS 调度） |
| | `GET /reviews/statistics` | 复习统计（总数 / 正确率 / Rating 分布） |
| **AI** | `POST /ai/upload` | 上传 PDF/DOCX/TXT/MD → AI 生成卡片 |
| | `POST /ai/generate` | 粘贴文本 → AI 生成卡片 |
| | `GET /ai/task/{id}` | 查询任务进度（前端轮询） |
| | `POST /ai/review-evaluate` | AI 评分复习回答 |
| **分析** | `GET /analytics/dashboard` | Dashboard 统计（今日待复习 / streak / 薄弱点） |
| | `GET /analytics/retention` | 记忆保持率预估（R = exp(-D/S)） |
| **计划** | `GET /goals` / `PUT /goals` | 获取 / 设置每日目标 |
| | `GET /goals/daily` | 今日目标完成进度 |
| **专项** | `GET /practice/mistakes` | 错题本（最近 Again 的卡片） |

---

## 🎨 界面预览

> 治愈系玻璃卡片风格，柔和的玫瑰粉、蜜桃、薄荷绿、木色配色

- 🏠 **Dashboard** — 4 张统计卡 + 学习趋势折线图 + 薄弱知识点 Top 5
- 🧠 **Review** — 选择题自动 rating（选对 → Good / 选错 → Again）+ 复习结束总结弹窗
- 🤖 **AI Studio** — 文档上传 + 粘贴生成 + 实时进度 + 批量审核
- 📊 **Analytics** — 复习统计 / 保持率预估 / Rating 饼图 / 知识库掌握度
- 📅 **Planner** — 今日目标进度条 + 错题本 + 目标设置
- 🏷️ **Tags** — 独立标签管理 + 颜色标记 + 使用次数统计

侧边栏实时显示**今日待复习徽章**，30 秒自动刷新。

---

## 🏛️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      Vue 3 Frontend                         │
│  Vite · Pinia · Element Plus · ECharts · Vue Router         │
│          ↕ axios (统一拦截器 + JWT)                          │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP
┌───────────────────────▼─────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐   │
│  │  Router    │  │   Service  │  │   DeepSeek API       │   │
│  │ (12 模块)  │→│  (6 层)    │→│   (AI 生成 / 评分)     │   │
│  └─────┬──────┘  └─────┬──────┘  └──────────────────────┘   │
│        ↓               ↓                                     │
│  ┌─────────────────────────┐  ┌─────────────────────────┐   │
│  │   FSRS 6.3.2 Engine     │  │   SQLAlchemy 2.0 ORM    │   │
│  │   (D/S/R 三参数调度)    │→│   (11 模型 + Alembic)    │   │
│  └─────────────────────────┘  └─────────────────────────┘   │
│                                    ↕                         │
│                          SQLite / PostgreSQL                  │
└─────────────────────────────────────────────────────────────┘
```

### 分层架构

```
Router (路由层, 12 个文件)
  ↓ 调用
Service (业务层, 6 个服务)
  ↓ 调用
Model / Schema (数据层)
  ↓
Database
```

### FSRS 调度流程

```
1. POST /reviews/start → 查到期卡片（due_at ≤ now）
2. 用户评分 Again/Hard/Good/Easy（1/2/3/4）
3. FSRS.update(schedule, rating) → 新的 D/S/R 三参数
4. 持久化：state / due_at / s / d / r → CardSchedule 表
5. 写入 ReviewLog：rating / time_ms / reviewed_at
```

---

## 🧪 测试

```bash
cd backend
pytest tests/ -v
```

```
tests/test_auth.py::test_register_then_login PASSED           [  7%]
tests/test_auth.py::test_duplicate_email_register_fails PASSED [ 14%]
tests/test_auth.py::test_wrong_login_password_fails PASSED     [ 21%]
tests/test_auth.py::test_protected_endpoint_rejects_no_token PASSED [ 28%]
tests/test_auth.py::test_protected_endpoint_accepts_token PASSED [ 35%]
tests/test_fsrs.py::test_create_card_has_schedule PASSED       [ 42%]
tests/test_fsrs.py::test_start_session_returns_cards PASSED    [ 50%]
tests/test_fsrs.py::test_submit_rating_updates_schedule PASSED  [ 57%]
tests/test_analytics.py::test_dashboard_stats_empty_user PASSED [ 64%]
tests/test_analytics.py::test_review_statistics_empty_user PASSED [ 71%]
tests/test_analytics.py::test_retention_empty_user PASSED       [ 78%]
tests/test_analytics.py::test_mistakes_empty_user PASSED        [ 85%]
tests/test_analytics.py::test_goals_daily_empty_user PASSED     [ 92%]
tests/test_analytics.py::test_batch_delete_bulk PASSED          [100%]

======================= 14 passed, 4 warnings in 3.18s ========================
```

测试特性：
- 使用 **StaticPool** 共享内存 SQLite，每个测试 fixture 独立
- FastAPI TestClient + `dependency_overrides` 注入测试 session
- 覆盖 Auth 鉴权 / FSRS 完整流程 / Analytics 空用户边界

---

## 🗄️ 数据库迁移

```bash
cd backend

# 创建新迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

当前已有 6 个迁移版本：
| 版本 | 说明 |
|---|---|
| `8f24ca4bcbc4` | 001 — 用户系统 |
| `a76e42ad183c` | 002 — 知识库 / 卡片 / 标签 |
| `65ac67640b0e` | 003 — 复习日志 / 调度 |
| `ec6dd2aceba1` | 004 — AI 任务 |
| `20df32106ef1` | 005 — 专项训练 |
| `7c38bc95df91` | 006 — 联想记忆 / 费曼 |

---

## 📝 License

MIT License

---

## 🌸 致谢

- [FSRS](https://github.com/open-spaced-repetition/fsrs4anki) — 科学的间隔重复算法
- [FastAPI](https://fastapi.tiangolo.com/) — 现代化的 Python Web 框架
- [Element Plus](https://element-plus.org/) — 优雅的 Vue 组件库
- [DeepSeek](https://www.deepseek.com/) — 优秀的 AI 推理模型
