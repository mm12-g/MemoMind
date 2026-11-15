# MemoMind 项目方案

> 基于开发需求 V1.0，完成项目分析、技术方案、数据库设计和开发任务拆分

---

## 一、项目分析

### 1.1 核心价值

MemoMind 解决的核心痛点：**用户有大量需要长期记忆的知识，但缺乏一个通用、智能、科学的记忆平台。**

产品闭环：**用户提供知识 → AI 整理知识 → FSRS 安排复习 → 用户主动回忆 → 学习分析发现薄弱点。**

### 1.2 功能模块依赖关系

```
用户中心 (基础)
  ├─ 知识库管理 (依赖用户)
  │    └─ 卡片系统 (依赖知识库)
  │         └─ FSRS 复习 (依赖卡片)
  │              └─ 复习历史 (依赖复习)
  ├─ AI Studio (独立，但生成结果写入知识库/卡片)
  ├─ 专项训练 (复用卡片系统)
  ├─ 学习分析 (依赖复习历史)
  └─ 学习计划 (依赖用户)
```

### 1.3 技术风险与解决方案

| 风险点 | 问题描述 | 解决方案 |
|--------|----------|----------|
| FSRS 库版本 | 需求文档未指定具体版本，API 变化可能影响集成 | 已确认使用 `fsrs==6.3.2`（官方最新稳定版），Card 对象字段与需求中 `card_schedules` 表设计略有差异，以库实际字段为准 |
| PostgreSQL 部署 | 本地开发需 PostgreSQL | 开发阶段可使用 Docker 快速启动，或先使用 SQLite（需配置切换）；生产必须 PostgreSQL |
| AI API Key 管理 | 多模型接入，密钥不能硬编码 | 使用 `.env` + Pydantic Settings 统一管理，支持多 Provider 配置 |
| FSRS 状态持久化 | 需求要求保存完整算法状态 | 直接存储 `Card.to_dict()` 的 JSON 表示，避免字段遗漏 |
| 异步任务 | AI 文档解析耗时较长 | 第一阶段先用同步接口 + 前端轮询，P1 阶段引入 Celery + Redis |
| 前端卡片类型渲染 | 4 种卡片类型，表单差异大 | 使用动态组件 + 统一接口约定，前端按 `card_type` 渲染不同表单 |

### 1.4 需求中发现的技术冲突

**冲突 1：FSRS card_schedules 表字段 vs 库实际 Card 字段**

需求文档定义的 `card_schedules` 字段（`reps`, `lapses`, `scheduled_days`, `elapsed_days`）在 FSRS v6.3.2 的 Card 对象中不存在。FSRS Card 只保留最核心的数学参数（`stability`, `difficulty`, `state`, `step`, `due`, `last_review`）。

**解决方案**：`card_schedules` 表以 FSRS Card 实际字段为准，额外字段（如 reps、lapses、计划间隔、实际间隔）从 review_logs 历史记录中统计计算。

**冲突 2：复习日志中的 `scheduled_days` 和 `elapsed_days`**

需求要求这两个字段，但 ReviewLog 对象本身不包含。

**解决方案**：这两个字段在提交复习时由后端计算（`elapsed_days = (now - last_review).days`，`scheduled_days = (new_due - now).days`），存入 review_logs。

---

## 二、技术方案

### 2.1 技术选型确认

| 层 | 技术 | 版本 | 选型理由 |
|----|------|------|----------|
| 后端语言 | Python | 3.12+ | FastAPI 生态成熟，FSRS 官方实现是 Python |
| Web 框架 | FastAPI | 最新 | 类型安全、异步、自动 OpenAPI 文档 |
| ORM | SQLAlchemy | 2.x | 异步支持、类型注解、成熟稳定 |
| 数据校验 | Pydantic | v2 | FastAPI 原生集成 |
| 数据库 | PostgreSQL | 16+ | JSONB 支持好、事务可靠 |
| 缓存/消息 | Redis | 7+ | 开发后期引入（Celery） |
| 异步任务 | Celery | 5+ | P1 阶段引入，处理 AI 文档解析 |
| 记忆算法 | fsrs | **6.3.2** | 官方 Python 实现，字段已确认 |
| 数据库迁移 | Alembic | 最新 | SQLAlchemy 官方迁移工具 |
| 前端框架 | Vue | 3.4+ | 响应式、组合式 API |
| 构建工具 | Vite | 5+ | 极速 HMR |
| UI 组件库 | Element Plus | 2+ | 中文友好、企业级组件齐全 |
| 状态管理 | Pinia | 2+ | Vue 3 官方推荐 |
| 图表 | ECharts | 5+ | 功能强大、文档完善 |
| HTTP 客户端 | Axios | 1+ | 拦截器、类型支持好 |
| 部署 | Docker + Docker Compose | - | 标准化部署 |

### 2.2 后端分层架构

```
backend/app/
├── main.py                    # FastAPI 应用入口
├── core/                      # 全局配置和基础设施
│   ├── config.py              # Pydantic Settings (.env 加载)
│   ├── security.py            # JWT、密码哈希
│   ├── database.py            # SQLAlchemy 引擎、Session
│   └── deps.py                # 依赖注入 (get_current_user, get_db)
├── models/                    # SQLAlchemy ORM 模型
│   ├── user.py
│   ├── deck.py
│   ├── card.py
│   ├── schedule.py            # FSRS Card 状态
│   ├── review_log.py
│   ├── tag.py
│   ├── study_session.py
│   ├── learning_goal.py
│   ├── source_document.py
│   ├── ai_task.py
│   └── ai_generation.py
├── schemas/                   # Pydantic 请求/响应模型
│   ├── common.py              # 统一响应格式
│   ├── auth.py
│   ├── user.py
│   ├── deck.py
│   ├── card.py                # 包含 4 种卡片类型的校验模型
│   ├── review.py
│   ├── tag.py
│   ├── ai.py
│   └── analytics.py
├── api/v1/                    # API 路由层（薄）
│   ├── router.py              # 汇总所有路由
│   ├── auth.py
│   ├── users.py
│   ├── decks.py
│   ├── cards.py
│   ├── reviews.py
│   ├── tags.py
│   ├── ai.py
│   └── analytics.py
├── services/                  # 业务逻辑层（厚）
│   ├── auth_service.py
│   ├── deck_service.py
│   ├── card_service.py
│   ├── review_service.py      # 复习编排 + FSRS 调用
│   ├── fsrs_service.py        # FSRS Scheduler 封装
│   ├── tag_service.py
│   ├── ai_service.py          # AI Provider 统一接口
│   ├── document_parser.py     # PDF/DOCX/TXT/MD 解析
│   ├── analytics_service.py
│   └── goal_service.py
└── ai/                        # AI 相关
    ├── provider.py             # AI Provider 抽象基类
    ├── providers/
    │   ├── deepseek.py        # DeepSeek 实现
    │   └── dashscope.py       # 阿里 DashScope 实现（可选）
    ├── card_generator.py      # 文档 → 卡片 生成器
    ├── answer_evaluator.py    # AI 答案评分
    └── prompts/               # Prompt 模板
        ├── card_generation.txt
        ├── answer_evaluation.txt
        └── question_generation.txt
```

### 2.3 数据流核心设计

#### 复习流程（最核心）

```
前端                          后端                         数据库
 │                            │                            │
 │  GET /reviews/due          │                            │
 │ ────────────────────────► │  查询 card_schedules        │
 │                            │  WHERE due <= now          │
 │                            │  AND state IN (1,2,3)      │
 │  返回待复习卡片列表         │                            │
 │ ◄──────────────────────── │ ◄────────────────────────── │
 │                            │                            │
 │  POST /reviews/submit      │                            │
 │  {card_id, rating, ...}    │                            │
 │ ────────────────────────► │  1. 校验用户归属              │
 │                            │  2. 加载 FSRS Card          │
 │                            │  3. scheduler.review_card() │
 │                            │  4. 计算 elapsed/scheduled │
 │                            │  5. 事务更新:               │
 │                            │     - card_schedules        │
 │                            │     - review_logs           │
 │                            │     - study_sessions       │
 │  返回下次复习时间           │                            │
 │ ◄──────────────────────── │ ──────────────────────────► │
```

#### 复习提交幂等方案

- 客户端生成 `review_token`（UUID），随每次提交发送
- 后端在 review_logs 表增加 `idempotency_key` 字段（唯一索引）
- 收到请求先查 idempotency_key，存在则直接返回上次结果
- token 有效期设为 10 分钟（Redis TTL 或数据库唯一约束 + 时间校验）

### 2.4 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

- `code = 0` 表示成功
- `code != 0` 表示错误（对应 HTTP 状态码语义）
- 分页接口 data 结构：`{"items": [...], "total": 100, "page": 1, "page_size": 20}`

### 2.5 统一异常处理

```python
class AppException(Exception):
    code: int           # HTTP 状态码
    message: str        # 错误描述
    detail: Any = None  # 额外信息

# 全局异常处理器统一返回格式
@app.exception_handler(AppException)
async def app_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.code,
        content={"code": exc.code, "message": exc.message, "data": exc.detail}
    )
```

### 2.6 FSRS 集成策略

**核心原则**：数据库只存 Card 的序列化 JSON（或等价字段），复习时完整还原 Card 对象，调用 Scheduler，再序列化回去。

```python
# 从数据库加载
card_dict = json.loads(schedule.fsrs_card_json)
card = Card.from_dict(card_dict)

# 执行复习
rating = Rating.Good
card, review_log = scheduler.review_card(card, rating)

# 保存回数据库
schedule.fsrs_card_json = card.to_json()
# 同时存入 review_logs
```

**为什么这样做？**
1. FSRS v6 的 Card 字段非常精简（只有 state, step, stability, difficulty, due, last_review），直接存 JSON 不浪费空间
2. 未来 FSRS 库升级时，只需更新 JSON 结构，不需要改数据库 schema
3. Card 对象原生支持 JSON 序列化/反序列化

---

## 三、数据库 ER 设计

### 3.1 ER 图（文本描述）

```
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│   users      │          │    decks    │          │   cards     │
├─────────────┤          ├─────────────┤          ├─────────────┤
│ id (PK)     │──┐       │ id (PK)     │──┐       │ id (PK)     │──┐
│ email       │  │       │ user_id(FK) │  │       │ deck_id(FK) │  │
│ username    │  ├──────►│ name        │  ├──────►│ card_type   │  │
│ password_   │  │  1:N  │ description │  │  1:N  │ front_      │  │
│   hash      │  │       │ category    │  │       │   content   │  │
│ status      │  │       │ created_at  │  │       │ back_       │  │
│ created_at  │  │       │ updated_at  │  │       │   content   │  │
│ updated_at  │  │       └─────────────┘  │       │ explanation │  │
└─────────────┘  │                        │       │ source_id   │  │
                 │                        │       │ created_at  │  │
                 │                        │       │ updated_at  │  │
                 │                        │       └──────┬──────┘  │
                 │                        │              │         │
                 │                        │              │1:1      │
                 │                        │              ▼         │
                 │                        │  ┌─────────────────────┴─────┐
                 │                        │  │      card_schedules       │
                 │                        │  ├────────────────────────────┤
                 │                        │  │ card_id (FK, PK)            │
                 │                        │  │ fsrs_card_json (JSONB)    │
                 │                        │  │ state (int)                │
                 │                        │  │ due_at (timestamptz)       │
                 │                        │  │ last_review_at            │
                 │                        │  │ created_at                 │
                 │                        │  │ updated_at                │
                 │                        │  └────────────────────────────┘
                 │                        │
                 │                        │       ┌─────────────┐
                 │                        │       │    tags    │
                 │                        │       ├─────────────┤
                 │                        │       │ id (PK)     │
                 │                        │       │ name       │
                 │                        │       │ user_id(FK) │
                 │                        │       │ color      │
                 │                        │       └──────┬──────┘
                 │                        │              │
                 │                        │   ┌─────────┴─────────┐
                 │                        │   │   card_tags      │
                 │                        │   ├─────────────────┤
                 │                        │   │ card_id (FK,PK)  │
                 │                        │   │ tag_id  (FK,PK)   │
                 │                        │   └─────────────────┘
                 │                        │
                 │                        │  ┌──────────────────────┐
                 │                        │  │     review_logs      │
                 │                        │  ├──────────────────────┤
                 │                        │  │ id (PK)               │
                 │                        │  │ user_id (FK)          │
                 │                        │  │ card_id (FK)          │
                 │                        │  │ session_id (FK,可空)  │
                 │                        │  │ rating                │
                 │                        │  │ reviewed_at           │
                 │                        │  │ elapsed_days         │
                 │                        │  │ scheduled_days        │
                 │                        │  │ response_time_ms      │
                 │                        │  │ answer_text          │
                 │                        │  │ ai_score             │
                 │                        │  │ idempotency_key      │
                 │                        │  └──────────────────────┘
                 │                        │
                 │                        │  ┌──────────────────────┐
                 │                        │  │   study_sessions    │
                 │                        │  ├──────────────────────┤
                 │                        │  │ id (PK)               │
                 │                        │  │ user_id (FK)          │
                 │                        │  │ started_at            │
                 │                        │  │ ended_at              │
                 │                        │  │ reviewed_count        │
                 │                        │  │ new_count             │
                 │                        │  │ duration_seconds      │
                 │                        │  └──────────────────────┘
                 │                        │
                 │                        │  ┌──────────────────────┐
                 │                        │  │   learning_goals    │
                 │                        │  ├──────────────────────┤
                 │                        │  │ id (PK)               │
                 │                        │  │ user_id (FK,唯一)    │
                 │                        │  │ daily_new_limit       │
                 │                        │  │ daily_review_limit    │
                 │                        │  │ daily_minutes_goal    │
                 │                        │  │ desired_retention     │
                 │                        │  │ created_at            │
                 │                        │  │ updated_at            │
                 │                        │  └──────────────────────┘
                 │                        │
                 │                        │  ┌──────────────────────┐
                 │                        │  │  source_documents   │
                 │                        │  ├──────────────────────┤
                 │                        │  │ id (PK)               │
                 │                        │  │ user_id (FK)          │
                 │                        │  │ filename              │
                 │                        │  │ file_path             │
                 │                        │  │ file_type             │
                 │                        │  │ file_size             │
                 │                        │  │ status                │
                 │                        │  │ created_at            │
                 │                        │  └──────────────────────┘
                 │                        │
                 │                        │  ┌──────────────────────┐
                 │                        │  │      ai_tasks        │
                 │                        │  ├──────────────────────┤
                 │                        │  │ id (PK)               │
                 │                        │  │ user_id (FK)          │
                 │                        │  │ task_type             │
                 │                        │  │ status                │
                 │                        │  │ progress             │
                 │                        │  │ error_message        │
                 │                        │  │ created_at           │
                 │                        │  │ completed_at         │
                 │                        │  └──────────────────────┘
                 │                        │
                 │                        │  ┌──────────────────────┐
                 │                        │  │   ai_generations    │
                 │                        │  ├──────────────────────┤
                 │                        │  │ id (PK)               │
                 │                        │  │ task_id (FK)          │
                 │                        │  │ output (JSONB)        │
                 │                        │  │ status                │
                 │                        │  │ approved_at          │
                 │                        │  │ created_at           │
                 │                        │  └──────────────────────┘
```

### 3.2 核心表字段详细设计

#### users
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 邮箱（登录凭证） |
| username | VARCHAR(100) | NOT NULL | 用户名（可重复） |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 哈希 |
| status | VARCHAR(20) | DEFAULT 'active' | active/disabled |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

#### decks
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | |
| user_id | INT | FK → users.id, NOT NULL | |
| name | VARCHAR(200) | NOT NULL | |
| description | TEXT | | |
| category | VARCHAR(50) | DEFAULT 'general' | 面试/考试/英语/日常 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**索引**: `(user_id)`, `(user_id, category)`

#### cards
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | |
| deck_id | INT | FK → decks.id, NOT NULL | |
| card_type | VARCHAR(20) | NOT NULL | basic/interview/choice/vocabulary |
| front_content | JSONB | NOT NULL | 正面内容（结构因类型而异） |
| back_content | JSONB | NOT NULL | 背面内容 |
| explanation | TEXT | | 补充解析 |
| source_id | INT | FK → source_documents.id | 来源文档，可空 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**front_content / back_content 结构示例**:

Basic 类型：
```json
// front_content: {"content": "什么是 list？"}
// back_content: {"content": "Python 的可变序列类型..."}
```

Interview 类型：
```json
// front_content: {"question": "list 和 tuple 的区别？", "keywords": ["可变", "不可变"]}
// back_content: {"answer": "list 可变...", "difficulty": 3}
```

Choice 类型：
```json
// front_content: {"question": "以下哪个是可变类型？", "options": ["list", "tuple", "str", "int"], "is_multiple": false}
// back_content: {"correct_answer": [0], "explanation": "..."}
```

Vocabulary 类型：
```json
// front_content: {"word": "ephemeral", "phonetic": "/ɪˈfemərəl/", "audio_url": null}
// back_content: {"cn_meaning": "短暂的", "en_meaning": "lasting a very short time", "examples": ["..."], "roots": ["..."], "synonyms": ["..."], "antonyms": ["..."]}
```

**索引**: `(deck_id)`, `(card_type)`, `GIN(front_content)`, `GIN(back_content)` — JSONB GIN 索引用于搜索

#### card_schedules（关键！FSRS 状态）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| card_id | INT | FK → cards.id, PK | 与卡片 1:1 |
| fsrs_card_json | JSONB | NOT NULL | FSRS Card.to_dict() 完整 JSON |
| state | INT | NOT NULL | 冗余索引字段: 1=Learning, 2=Review, 3=Relearning |
| due_at | TIMESTAMPTZ | NOT NULL | 冗余索引字段 |
| last_review_at | TIMESTAMPTZ | | 冗余索引字段 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**说明**: 为什么同时存 JSON 和单独字段？
- `fsrs_card_json` 是完整权威数据，用于还原 Card 对象
- `state` 和 `due_at` 是冗余字段，用于快速查询（查到期卡片不需要解析 JSONB）
- 两者必须在同一事务中更新，保持一致

**索引**: `(state, due_at)` — 查询今日到期的核心索引

#### review_logs
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGSERIAL | PK | |
| user_id | INT | FK → users.id, NOT NULL | |
| card_id | INT | FK → cards.id, NOT NULL | |
| session_id | INT | FK → study_sessions.id | |
| rating | INT | NOT NULL | 1=Again, 2=Hard, 3=Good, 4=Easy |
| reviewed_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| elapsed_days | INT | | 实际间隔天数 |
| scheduled_days | INT | | 计划间隔天数 |
| response_time_ms | INT | | 回答耗时（毫秒） |
| answer_text | TEXT | | 用户回答文本 |
| ai_score | JSONB | | AI 评分结果，可空 |
| idempotency_key | VARCHAR(64) | UNIQUE | 幂等键 |

**索引**: `(card_id)`, `(user_id, reviewed_at)`, `(user_id, reviewed_at DESC)` — 统计查询

#### tags / card_tags
| 表 | 字段 | 类型 | 约束 |
|----|------|------|------|
| tags | id | SERIAL | PK |
| | user_id | INT | FK → users.id |
| | name | VARCHAR(50) | NOT NULL |
| | color | VARCHAR(20) | |
| card_tags | card_id | INT | FK → cards.id, PK |
| | tag_id | INT | FK → tags.id, PK |

#### study_sessions
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | |
| user_id | INT | FK → users.id, NOT NULL | |
| started_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| ended_at | TIMESTAMPTZ | | |
| reviewed_count | INT | DEFAULT 0 | |
| new_count | INT | DEFAULT 0 | |
| duration_seconds | INT | | 结束时计算 |

#### learning_goals
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | |
| user_id | INT | FK → users.id, UNIQUE, NOT NULL | 每个用户只有一套目标 |
| daily_new_limit | INT | DEFAULT 20 | |
| daily_review_limit | INT | DEFAULT 200 | |
| daily_minutes_goal | INT | DEFAULT 30 | |
| desired_retention | FLOAT | DEFAULT 0.9 | |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

#### source_documents
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | |
| user_id | INT | FK → users.id, NOT NULL | |
| filename | VARCHAR(255) | NOT NULL | |
| file_path | VARCHAR(500) | NOT NULL | |
| file_type | VARCHAR(20) | NOT NULL | pdf/docx/txt/md |
| file_size | BIGINT | NOT NULL | |
| status | VARCHAR(20) | DEFAULT 'uploaded' | uploaded/parsed/failed |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

#### ai_tasks / ai_generations
| 表 | 字段 | 类型 | 约束 | 说明 |
|----|------|------|------|------|
| ai_tasks | id | SERIAL | PK | |
| | user_id | INT | FK | |
| | task_type | VARCHAR(50) | | document_parse/card_generate/answer_evaluate/question_generate |
| | status | VARCHAR(20) | DEFAULT 'pending' | pending/processing/completed/failed |
| | progress | INT | DEFAULT 0 | 0-100 |
| | error_message | TEXT | | |
| | deck_id | INT | FK | 目标知识库（可空） |
| | source_document_id | INT | FK | 来源文档（可空） |
| | created_at | TIMESTAMPTZ | | |
| | completed_at | TIMESTAMPTZ | | |
| ai_generations | id | SERIAL | PK | |
| | task_id | INT | FK → ai_tasks.id, NOT NULL | |
| | output | JSONB | NOT NULL | AI 生成的卡片/评分结果 |
| | status | VARCHAR(20) | DEFAULT 'pending' | pending/approved/rejected |
| | approved_at | TIMESTAMPTZ | | |
| | created_at | TIMESTAMPTZ | | |

### 3.3 数据库索引设计总结

| 表 | 索引 | 类型 | 用途 |
|----|------|------|------|
| users | email | UNIQUE | 登录查询 |
| decks | (user_id) | BTREE | 用户知识库列表 |
| cards | (deck_id) | BTREE | 知识库卡片列表 |
| cards | card_type | BTREE | 按类型筛选 |
| cards | front_content | GIN | 全文/结构化搜索 |
| cards | back_content | GIN | 全文/结构化搜索 |
| card_schedules | (state, due_at) | BTREE | **查询到期卡片（核心性能）** |
| review_logs | (user_id, reviewed_at) | BTREE | 学习统计 |
| review_logs | (card_id) | BTREE | 卡片复习历史 |
| review_logs | idempotency_key | UNIQUE | 幂等约束 |
| review_logs | (user_id, DATE(reviewed_at)) | 覆盖 | 每日学习统计（可用物化视图替代） |

### 3.4 数据库迁移计划

```
Alembic 迁移文件：

001_initial_tables
  ├── users
  ├── decks
  ├── cards
  ├── card_schedules
  ├── tags + card_tags
  ├── study_sessions
  ├── learning_goals (种子数据：为每个新用户自动创建一套默认目标)

002_review_logs_and_ai
  ├── review_logs
  ├── source_documents
  ├── ai_tasks
  └── ai_generations
```

---

## 四、开发任务拆分

### 阶段总览

| 阶段 | 内容 | 预估 | 优先级 |
|------|------|------|--------|
| P1 | 基础环境 + 用户认证 | 2 天 | P0 |
| P2 | 知识库 + 卡片系统 | 3 天 | P0 |
| P3 | FSRS 复习系统 | 3 天 | P0 |
| P4 | Dashboard + 统计 + 目标 | 2 天 | P0 |
| P5 | AI Studio（文档解析 + 卡片生成 + 评分） | 4 天 | P1 |
| P6 | 专项训练（面试 + 考试 + 英语） | 3 天 | P1 |
| P7 | 测试 + 部署 + 优化 | 3 天 | P0 |

### 阶段 P1：基础环境 + 用户认证（第 1-2 天）

**后端任务**:
- [ ] 创建项目结构 `backend/app/`
- [ ] 配置 `pyproject.toml` 或 `requirements.txt`（FastAPI, SQLAlchemy, Pydantic v2, psycopg2-binary, bcrypt, python-jose, alembic）
- [ ] 编写 `.env.example` 和 `backend/app/core/config.py`（Pydantic Settings）
- [ ] 编写 `backend/app/core/database.py`（异步 Session 支持先不开，同步即可）
- [ ] 编写 `backend/app/core/security.py`（密码哈希 + JWT 工具函数）
- [ ] 编写 alembic 初始化配置
- [ ] 创建 `users` 表模型 + 迁移
- [ ] 实现 `/api/v1/auth/register` 接口
- [ ] 实现 `/api/v1/auth/login` 接口（返回 JWT access_token）
- [ ] 实现 `get_current_user` 依赖注入
- [ ] 实现 `/api/v1/users/me` GET/PUT
- [ ] 实现健康检查 `/health`
- [ ] 编写全局异常处理 + 统一响应
- [ ] 编写 Pytest 基础配置 + auth 测试

**前端任务**:
- [ ] 创建 Vue 3 + TypeScript + Vite 项目
- [ ] 安装 Element Plus、Pinia、Vue Router、Axios
- [ ] 编写项目目录结构（api, stores, router, layouts, views）
- [ ] 配置 Axios 实例（Base URL, Token 拦截器, 统一错误处理）
- [ ] 编写登录页 `/login`
- [ ] 编写注册页 `/register`
- [ ] 编写基础后台布局（侧边栏 + 顶部 + 内容区）
- [ ] 配置路由守卫（未登录跳转）
- [ ] 编写 auth store

**验收标准**: 用户可注册 → 登录 → 获取 JWT → 访问受保护接口，前后端联通。

---

### 阶段 P2：知识库 + 卡片系统（第 3-5 天）

**后端任务**:
- [ ] 创建 `decks` 表模型 + 迁移
- [ ] 创建 `cards` 表模型 + 迁移
- [ ] 创建 `tags` + `card_tags` 表模型 + 迁移
- [ ] 实现 Deck CRUD 接口（完整归属校验）
- [ ] 实现 Card CRUD 接口（完整归属校验）
- [ ] 实现 4 种卡片类型的 Pydantic 校验模型（Basic/Interview/Choice/Vocabulary）
- [ ] 实现卡片搜索接口（deck_id 范围 + 关键词匹配 JSONB 字段）
- [ ] 实现 Tag CRUD + 卡片标签关联
- [ ] 实现 `POST /cards/import`（CSV 格式批量导入）
- [ ] 编写 Card 类型校验测试

**前端任务**:
- [ ] 编写知识库列表页 `/decks`（创建/编辑/删除/搜索）
- [ ] 编写知识库详情页 `/decks/:id`（卡片列表 + 统计）
- [ ] 编写卡片创建/编辑页 `/decks/:id/cards/new`（4 种类型动态表单）
- [ ] 编写卡片详情页 `/cards/:id`
- [ ] 编写标签管理
- [ ] 编写批量导入 UI
- [ ] 统一卡片组件（根据 card_type 渲染不同展示）

**验收标准**: 用户可创建知识库 → 添加至少 100 张 4 种类型的卡片 → 搜索/编辑/删除正常工作。

---

### 阶段 P3：FSRS 复习系统（第 6-8 天）

**后端任务**:
- [ ] `pip install fsrs==6.3.2`
- [ ] 创建 `card_schedules` 表 + 迁移（含初始状态：新卡片 due_at = now()）
- [ ] 创建 `review_logs` 表 + 迁移
- [ ] 创建 `study_sessions` 表 + 迁移
- [ ] 创建 `learning_goals` 表 + 迁移（新用户注册时自动创建默认目标）
- [ ] 编写 `services/fsrs_service.py`（Scheduler 封装，支持从目标 retention 配置）
- [ ] 编写 `services/review_service.py`（复习流程编排）
- [ ] 实现卡片创建时自动初始化 card_schedules（新卡片状态 = Learning, due = now()）
- [ ] 实现 `GET /reviews/due`（查询 state IN (1,2,3) 且 due_at <= now() 的卡片）
- [ ] 实现 `POST /reviews/start`（创建 study_session，返回 session_id + 首批卡片）
- [ ] 实现 `POST /reviews/submit`（**核心接口**：事务内完成 FSRS 调度 + 状态更新 + 日志写入，含幂等机制）
- [ ] 实现 `GET /reviews/history`（某卡片或某时间段复习历史）
- [ ] 实现复习提交的 FSRS 单元测试（4 种 rating × 新卡片 × 复习中卡片 × 遗忘卡片）

**前端任务**:
- [ ] 编写复习页面 `/review`（核心页面）
  - [ ] 顶部：当前复习进度 + 退出按钮
  - [ ] 中部：卡片正面（默认隐藏答案）+ 显示答案按钮
  - [ ] 底部：输入回答框（可选）+ 4 个反馈按钮
  - [ ] 提交后自动下一张
  - [ ] 结束时显示学习总结（本次复习数、正确率、平均耗时）
- [ ] 复习状态管理（Pinia store）
- [ ] 加载/提交状态的错误处理

**验收标准**: 完整闭环 — 添加卡片 → 开始学习 → 查看卡片 → 反馈 Good/Hard/Easy/Again → 自动安排下一次复习时间 → 复习历史可查。

---

### 阶段 P4：Dashboard + 统计 + 目标（第 9-10 天）

**后端任务**:
- [ ] 编写 `services/analytics_service.py`
- [ ] 实现 `GET /analytics/dashboard`（今日统计 + 薄弱知识点）
- [ ] 实现 `GET /analytics/trend`（7/30 天学习趋势：每日复习数、新增数、正确率、学习时长）
- [ ] 实现 `GET /analytics/decks`（各知识库掌握情况统计）
- [ ] 实现 `GET /analytics/weak-points`（经常遗忘的卡片/知识点）
- [ ] 实现 `GET /analytics/retention`（记忆保持率估算）
- [ ] 实现学习计划相关接口（每日目标设置 + 完成情况查询）

**前端任务**:
- [ ] 编写 Dashboard 首页 `/dashboard`
  - [ ] 顶部 4 个统计卡片（今日待复习、今日新增、已掌握、连续学习天数）
  - [ ] 今日任务列表
  - [ ] 学习趋势图（ECharts，最近 7 天）
  - [ ] 薄弱知识点列表
- [ ] 编写学习分析页 `/analytics`
  - [ ] 各知识库掌握程度分布
  - [ ] 详细趋势（可切换 7/30 天）
  - [ ] 遗忘分析
- [ ] 编写学习计划页 `/planner`（目标设置 + 日历视图）

**验收标准**: Dashboard 数据真实反映用户学习情况；学习目标可设置、可查看完成进度。

---

### 阶段 P5：AI Studio（第 11-14 天）

**后端任务**:
- [ ] 编写 `core/config.py` 增加 AI Provider 配置（DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, AI_PROVIDER）
- [ ] 编写 `ai/provider.py`（AI Provider 抽象基类 + DeepSeek 实现）
- [ ] 编写 `services/document_parser.py`（PyMuPDF, python-docx, 标准文本处理）
- [ ] 编写 `ai/prompts/` 目录 + Prompt 模板
- [ ] 编写 `ai/card_generator.py`（文档 → 知识点提取 → 卡片生成 → Pydantic 校验）
- [ ] 编写 `ai/answer_evaluator.py`（AI 评分，返回结构化 JSON）
- [ ] 创建 `source_documents` + `ai_tasks` + `ai_generations` 表 + 迁移
- [ ] 实现 `POST /ai/documents/upload`（文件上传 + 类型校验 + 大小限制 + 返回 task_id）
- [ ] 实现 `POST /ai/cards/generate`（指定来源文本 + 目标类型 + 目标 deck → 生成卡片）
- [ ] 实现 `POST /ai/questions/generate`（指定内容 → 生成练习题）
- [ ] 实现 `POST /ai/answers/evaluate`（用户回答 + 参考答案 → AI 评分）
- [ ] 实现 `GET /ai/tasks/{id}`（查询任务状态 + 进度）
- [ ] 实现 `POST /ai/generations/{id}/approve`（审核生成结果 → 保存为正式卡片）
- [ ] 第一阶段先用同步方式处理（接口内部先返回 task_id，AI 处理在后台线程完成，前端轮询状态）

**前端任务**:
- [ ] 编写 AI 工作台 `/ai-studio`
  - [ ] 文件上传区（拖拽 + 点击，支持 PDF/DOCX/TXT/MD）
  - [ ] 任务进度条
  - [ ] 生成结果列表（卡片预览 + 编辑）
  - [ ] 批量批准/删除
- [ ] 编写 AI 出题入口（在 AI 工作台内）
- [ ] 复习页面集成 AI 评分入口

**验收标准**: 上传一份 Python 面试题文档 → AI 生成 20-30 张卡片 → 用户审核 → 保存到知识库。

---

### 阶段 P6：专项训练（第 15-17 天）

**后端任务**:
- [ ] 实现面试训练随机抽题接口（从 Interview 类型卡片中随机，可按 deck 或分类筛选）
- [ ] 实现考试训练接口（Choice 卡片按考试模式组织）
- [ ] 实现英语训练接口（Vocabulary 卡片的多种练习方式：看英文选中文、拼写测试）
- [ ] 错题回顾接口（筛选 review_logs 中 rating=1 的卡片）

**前端任务**:
- [ ] 编写面试训练页 `/practice/interview`（随机抽题 + AI 评分入口 + 统计）
- [ ] 编写考试训练页 `/practice/exam`（按知识库组卷 + 答题 + 提交 + 错题回看）
- [ ] 编写英语训练页 `/practice/vocabulary`（多种模式切换 + 拼写测试）

**验收标准**: 三种训练模式均可从知识库抽取对应类型的卡片进行练习，与 FSRS 复习体系互通。

---

### 阶段 P7：测试 + 部署 + 优化（第 18-20 天）

**后端任务**:
- [ ] 编写完整 Pytest 测试
  - [ ] Auth 测试（注册/登录/Token 刷新）
  - [ ] 数据隔离测试（用户 A 不能访问用户 B 的资源）
  - [ ] FSRS 测试（4 种 rating × 状态转换 × 时间计算）
  - [ ] 复习事务测试（模拟事务回滚）
  - [ ] 幂等测试（同一 token 不产生重复记录）
  - [ ] AI 输出校验测试（错误 JSON 被拒绝）
- [ ] Dockerfile 编写（后端多阶段构建）
- [ ] docker-compose.yml（backend + postgres + redis + nginx）
- [ ] Nginx 配置（反向代理 + 静态文件 + HTTPS）
- [ ] .env.example 完善
- [ ] README 编写（启动方式、开发指南、API 文档链接）

**前端任务**:
- [ ] Dockerfile 编写（构建静态文件 + Nginx 托管）
- [ ] 前端部署配置

**验收标准**: `docker-compose up` 一键启动 → 访问前端页面 → 完整注册 → 创建知识库 → 添加卡片 → 复习 → AI 生成卡片 → 统计 → 全流程无阻塞。

---

## 五、API 接口清单（确认版）

### 5.1 Auth
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/register | 注册，返回 user_id |
| POST | /api/v1/auth/login | 登录，返回 access_token |
| POST | /api/v1/auth/refresh | 刷新 Token（可选） |

### 5.2 Users
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/users/me | 获取当前用户信息 |
| PUT | /api/v1/users/me | 修改用户信息 |

### 5.3 Decks
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/decks | 创建知识库 |
| GET | /api/v1/decks | 列表（分页） |
| GET | /api/v1/decks/{id} | 详情（含卡片统计） |
| PUT | /api/v1/decks/{id} | 修改 |
| DELETE | /api/v1/decks/{id} | 删除（级联删除卡片+调度+日志） |

### 5.4 Cards
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/cards | 创建卡片 |
| GET | /api/v1/cards | 列表（支持 deck_id, card_type, 关键词筛选） |
| GET | /api/v1/cards/{id} | 详情 |
| PUT | /api/v1/cards/{id} | 修改 |
| DELETE | /api/v1/cards/{id} | 删除（级联） |
| POST | /api/v1/cards/import | CSV 批量导入 |

### 5.5 Reviews
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/reviews/due | 查看到期卡片（含 state, due_at 筛选） |
| POST | /api/v1/reviews/start | 开始学习会话，返回 session_id + 首批卡片 |
| POST | /api/v1/reviews/submit | **提交复习结果**（核心接口） |
| GET | /api/v1/reviews/history | 复习历史（支持 card_id、日期范围筛选） |
| GET | /api/v1/reviews/statistics | 复习统计 |

### 5.6 Analytics
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/analytics/dashboard | Dashboard 数据 |
| GET | /api/v1/analytics/trend | 学习趋势（7/30 天） |
| GET | /api/v1/analytics/decks | 各知识库统计 |
| GET | /api/v1/analytics/weak-points | 薄弱知识点 |
| GET | /api/v1/analytics/retention | 记忆保持率 |

### 5.7 Goals
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/goals | 获取当前目标 |
| PUT | /api/v1/goals | 更新目标 |
| GET | /api/v1/goals/daily | 今日目标完成情况 |

### 5.8 Tags
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/tags | 创建标签 |
| GET | /api/v1/tags | 标签列表 |
| PUT | /api/v1/tags/{id} | 修改 |
| DELETE | /api/v1/tags/{id} | 删除 |
| POST | /api/v1/cards/{id}/tags | 关联标签 |
| DELETE | /api/v1/cards/{id}/tags/{tag_id} | 取消关联 |

### 5.9 AI
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/ai/documents/upload | 上传文档，返回 task_id |
| POST | /api/v1/ai/cards/generate | 从文本生成卡片 |
| POST | /api/v1/ai/questions/generate | AI 出题 |
| POST | /api/v1/ai/answers/evaluate | AI 答案评分 |
| GET | /api/v1/ai/tasks/{id} | 查询任务状态 |
| GET | /api/v1/ai/generations | 生成结果列表（支持 task_id 筛选） |
| POST | /api/v1/ai/generations/{id}/approve | 审核并保存 |
| DELETE | /api/v1/ai/generations/{id} | 拒绝 |

### 5.10 Practice
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/practice/interview/start | 面试训练开始（返回卡片列表） |
| GET | /api/v1/practice/exam/start | 考试训练开始 |
| GET | /api/v1/practice/vocabulary/start | 英语训练开始 |
| GET | /api/v1/practice/mistakes | 错题列表 |

---

## 六、关键决策记录

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 异步 I/O | 第一版用同步 SQLAlchemy | 减少复杂度，PostgreSQL 驱动足够快；异步迁移成本可控 |
| FSRS 存储 | Card JSONB + 冗余索引字段 | JSONB 保留完整状态，冗余字段保证查询性能 |
| 异步任务 | P0 阶段不用 Celery | 同步处理 + 后台线程足够；P1 再引入 Redis + Celery |
| AI  Provider | 先支持 DeepSeek，抽象接口扩展 | DeepSeek 性价比高，接口通用 |
| 用户数据隔离 | 后端所有查询强制注入 user_id | SQLAlchemy session 级别拦截或显式 WHERE |
| 复习幂等 | idempotency_key 唯一索引 | 简单可靠，不需要 Redis |
| 时间存储 | 统一 TIMESTAMPTZ（UTC） | 前后端各自处理时区展示 |

---

## 七、启动方式

### 开发环境

```bash
# 1. 启动 PostgreSQL（Docker）
docker run -d --name memomind-pg -e POSTGRES_USER=memomind -e POSTGRES_PASSWORD=memomind -e POSTGRES_DB=memomind -p 5432:5432 postgres:16

# 2. 后端
cd backend
python -m venv venv && venv\Scripts\activate     # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. 前端
cd frontend
npm install
npm run dev   # 默认 http://localhost:5173
```

### 生产部署

```bash
docker-compose up -d
# 前端: http://localhost
# 后端API: http://localhost/api/v1
```

---

**文档状态**: 待用户确认  
**确认后**: 按阶段 P1 → P7 顺序执行开发
