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
├── backend/                # 后端（Flask）
│   ├── app.py              # 入口文件
│   ├── config.py           # 配置（数据库、密钥、第三方 API Key）
│   ├── requirements.txt    # Python依赖
│   │
│   ├── common/             # 公共模块
│   │   ├── utils.py        # 工具函数
│   │   ├── jwt_auth.py     # Token 认证
│   │   └── validators.py   # 参数校验
│   │
│   ├── database/           # 数据库模型 & 初始化
│   │   ├── db.py           # SQLAlchemy初始化
│   │   ├── models.py       # Users / Records / Collections / NFTs
│   │   └── migrations/     # 数据库迁移（Alembic）
│   │
│   ├── routes/             # 控制器（接口）
│   │   ├── auth.py         # 注册 / 登录 / 重置密码
│   │   ├── user.py         # 用户资料修改
│   │   ├── generation.py   # 生成任务相关 API
│   │   ├── upload.py       # 上传接口
│   │   ├── records.py      # 生成记录管理
│   │   ├── collections.py  # 收藏夹管理
│   │   ├── nft.py          # NFT 铸造、查询
│   │   └── admin.py        # 管理员接口
│   │
│   ├── services/           # 业务逻辑层（核心逻辑放这里）
│   │   ├── generation_service.py  # 文生图 / 图生图 / 文生视频调度
│   │   ├── queue_service.py        # 异步任务调度（Celery / RQ）
│   │   ├── nft_service.py          # 链上铸造逻辑（IPFS、NFTPort）
│   │   ├── email_service.py        # 邮件发送与验证码
│   │   └── file_service.py         # 文件保存、清洗
│   │
│   └── tasks/               # 异步队列执行器
│       ├── worker.py
│       └── task_def.py
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