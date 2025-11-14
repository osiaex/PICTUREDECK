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
├── run.py                 # ✅ 项目启动文件，直接 python run.py 就能跑
├── requirements.txt       # ✅ 项目依赖，就那几个核心的
├── config.py              # ✅ 配置文件，数据库连接放这里
└── app/                   # ⭐️ 我们的核心代码都在这里
    ├── __init__.py        # 初始化Flask App，注册蓝图
    ├── models.py          # 数据库模型，Users/Generations/Collections/NFTs 四个类全放这
    ├── services/          # 核心逻辑层 (可选，但建议有)
    │   └── generation_service.py  # 比如调用AI模型的核心逻辑放这里，让接口更干净
    ├── routes/            # ⭐️ 所有的接口(API)都在这里。
    │   ├── __init__.py
    │   ├── auth_routes.py       # 用户注册、登录接口
    │   ├── generation_routes.py # 发起生成、查询结果接口
    │   ├── collection_routes.py # 文件夹、文件管理接口
    │   └── nft_routes.py        # NFT相关接口
    └── utils/             # 存放通用工具
        └── helpers.py         # 比如统一的JSON返回格式函数
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