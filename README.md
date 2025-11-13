PICTUREDECK/
│
├── README.md               # 项目说明文档（项目介绍 + 运行方式 + 架构图）
├── LICENSE                 # 开源协议（MIT / Apache-2.0）
├── .gitignore
│
├── docs/                   # 文档区（设计文档、接口文档、部署文档等）
│   ├── DESIGN_DOCUMENT.md  # 你上传的 Word 版设计文档转写
│   ├── API_REFERENCE.md    # 按 RESTful API 分类整理接口
│   ├── DATABASE_SCHEMA.md  # 数据库结构说明（Users/Records/NFTs）
│   ├── ARCHITECTURE.md     # 架构图、流程图
│   └── DEPLOYMENT.md       # 部署方案（Flask + Nginx + HTTPS + SQLite/PostgreSQL）
│
backend/
├── app/
│   ├── main.py                 # FastAPI 应用入口, 挂载路由, 配置中间件
│   ├── requirements.txt        # Python 依赖包
│   └── .env                    # 环境变量文件 (数据库链接, 密钥等)
│   
│   ├── api/                    # API 路由层 (HTTP接口)
│   │   ├── deps.py             # 依赖注入函数 (获取DB会话, 获取当前用户等)
│   │   └── v1/                 # API 版本 1
│   │       ├── __init__.py
│   │       ├── auth.py         # 认证路由 (登录, 注册, 密码重置)
│   │       ├── users.py        # 用户信息路由 (查询/更新个人资料)
│   │       ├── generation.py   # 内容生成任务路由 (提交任务, 查询状态)
│   │       ├── records.py      # 生成作品管理路由 (列表, 详情, 删除, 修改)
│   │       ├── collections.py  # 文件夹/收藏夹管理路由 (增删改查, 添加/移除作品)
│   │       ├── assets.py       # 上传资源路由 (用于图生图、图生视频等)
│   │     
│   │
│   ├── core/                   # 核心模块
│   │   ├── config.py           # 应用配置 (使用 Pydantic BaseSettings 读取 .env)
│   │   └── security.py         # 安全相关 (密码哈希, JWT 创建与解码)
│   │
│   ├── crud/                   # 数据访问层 (封装数据库的增删改查)
│   │   ├── __init__.py
│   │   ├── base.py             # (可选) 通用 CRUD 操作基类
│   │   ├── crud_user.py        # User 模型的 CRUD 操作
│   │   ├── crud_generation_task.py # GenerationTask 模型的 CRUD 操作
│   │   ├── crud_generated_record.py # GeneratedRecord 模型的 CRUD 操作
│   │   ├── crud_collection.py  # Collection 模型的 CRUD 操作
│   │   └── crud_uploaded_asset.py # UploadedAsset 模型的 CRUD 操作
│   │
│   ├── db/                     # 数据库模块
│   │   ├── __init__.py
│   │   ├── base.py             # 声明式模型基类 (Base = declarative_base())
│   │   ├── models.py           # 所有 SQLAlchemy 模型定义 (基于你的DDL)
│   │   └── session.py          # 数据库引擎和 SessionLocal 创建
│   │
│   ├── schemas/                # Pydantic 模型层 (定义 API 的数据接口)
│   │   ├── __init__.py
│   │   ├── user.py             # User 相关的 Pydantic Schemas 
│   │   ├── token.py            # JWT Token 相关的 Schemas (Token, TokenData)
│   │   ├── task.py             # GenerationTask 相关的 Schemas (TaskCreate, Task)
│   │   ├── record.py           # GeneratedRecord 相关的 Schemas 
│   │   ├── collection.py       # Collection 相关的 Schemas 
│   │   ├── asset.py            # UploadedAsset 相关的 Schemas (Asset)
│   │   └── message.py          # 通用的消息响应 Schema 
│   │
│   ├── services/               # 业务逻辑层 (编排复杂业务流程)
│   │   ├── user_service.py     # 用户注册、登录、权限等复杂逻辑
│   │   ├── generation_service.py # 调用AI模型、处理生成逻辑
│   │   ├── queue_service.py    # 异步任务调度 (与 Celery/RQ 集成)
│   │   ├── file_service.py     # 文件处理逻辑 (与云存储 S3/OSS 交互)
│   │   └── email_service.py    # (可选) 邮件发送服务 (验证码, 通知)
│   │
│   ├── tasks/                  # 异步任务定义
│   │   ├── __init__.py
│   │   ├── worker.py           # Celery/RQ worker 启动配置
│   │   └── generation_tasks.py # 定义具体的生成任务 (e.g., @celery.task)
│   │
│   └── utils/                  # 通用工具函数
│       ├── __init__.py
│       └── helpers.py          # 不属于任何特定领域的辅助函数
│
└── tests/                      # 测试目录
|   ├── __init__.py
|   ├── conftest.py             # Pytest fixtures (e.g., 创建测试数据库, 测试客户端)
|   │
|   ├── api/
|   │   └── v1/
|   │       ├── test_auth.py
|   │       ├── test_users.py
|   │       └── test_generation.py
|   │
|   ├── crud/
|   │   └── test_crud_user.py
|   │
|   └── services/
|       └── test_generation_service.py
|
│
├── frontend/                 # 前端（任选其一：Qt / Web / Flutter Desktop）
│   ├── web/                 # 如用 Web UI
│   │   ├── index.html
│   │   ├── src/
│   │   │   ├── pages/       # 登录/注册/生成/画廊/个人资料
│   │   │   ├── components/
│   │   │   ├── api/         # axios 封装的后端接口
│   │   │   └── assets/
│   │   └── package.json
│   │
│   └── qt/                  # 如使用 PyQt / Qt Designer
│       ├── main_window.ui
│       ├── main.py
│       └── components/
│
├── storage/                  # 图片/视频生成结果存放（可换成 cloud + CDN）
│   ├── uploads/             # 上传图片
│   └── results/             # AI生成内容
│
├── scripts/                  # 辅助脚本
│   ├── init_db.py           # 数据库初始化
│   ├── run_dev.sh           # 本地启动脚本
│   └── deploy.sh            # 自动化部署脚本
│
└── tests/                    # 单元测试
    ├── test_auth.py
    ├── test_generation.py
    ├── test_nft.py
    ├── test_records.py
    └── test_admin.py