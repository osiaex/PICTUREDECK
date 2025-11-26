# PICTUREDECK 项目最小可用框架结构（基于《PICTUREDECK 设计文档》）

目标：在不复杂化的前提下，覆盖用户、生成任务、生成结果记录、资源与集合管理，并在“最精简”的实现路径下保证 NFT 功能可落地（支持占位模式与 EVM 测试网真实上链模式）。

原则：单体应用、清晰分层、少而精的模块；能跑、能迭代；默认最少依赖，按需启用链上能力。

---

## 技术栈（最小配置）
- 后端：FastAPI + Pydantic + SQLAlchemy
- 数据库：SQLite（开发）/ PostgreSQL（生产）
- 认证：JWT（基于 `core/security.py`）
- 存储：本地文件系统（`storage/uploads`、`storage/results`、`storage/metadata`）
- 前端：纯静态 Web（原生 HTML/CSS/JS + fetch），零构建；可平滑升级至 Vite + Vue/React
- NFT（链上模式可选）：web3.py（EVM 测试网，如 Sepolia），标准 ERC-721 合约（需配置合约地址）

---

## 顶层目录结构（保持精简，同时保证 NFT 可实现）
```
PICTUREDECK/
├── backend/
│   ├── app/
│   │   ├── main.py                 # 创建 FastAPI 应用、注册路由、挂载静态资源（/web、/files、/metadata）
│   │   ├── api/
│   │   │   ├── deps.py             # 依赖注入（DB 会话、当前用户）
│   │   │   └── v1/
│   │   │       ├── auth.py         # 注册、登录
│   │   │       ├── users.py        # 用户查询/更新（最小）
│   │   │       ├── generation.py   # 生成任务提交/查询状态
│   │   │       ├── records.py      # 生成结果记录查询
│   │   │       ├── collections.py  # （可选）集合管理
│   │   │       ├── assets.py       # 资源上传/下载
│   │   │       └── **nft.py**          # NFT 铸造/查询（新增，最小实现）
│   │   ├── core/
│   │   │   ├── config.py           # 配置：DB/JWT/存储路径/链上配置（provider、私钥、合约地址）
│   │   │   └── security.py         # JWT、密码哈希
│   │   ├── models/                 # ORM 模型
│   │   │   ├── user.py
│   │   │   ├── generation_task.py
│   │   │   ├── generated_record.py
│   │   │   └── **nft.py**              # 新增：NFT 模型（最小字段）
│   │   ├── schemas/                # Pydantic 模型
│   │   │   ├── user.py
│   │   │   ├── generation_task.py
│   │   │   ├── generated_record.py
│   │   │   └── **nft.py**              # 新增：NFT 请求/响应模型
│   │   ├── services/
│   │   │   ├── generation_service.py # 生成任务（初期同步占位即可）
│   │   │   └── **nft_service.py**        # 新增：NFT 铸造服务（占位/链上两种模式）
│   │   └── utils/                   # 可选：统一响应等
│   └── crud/
│       ├── base.py
│       ├── crud_user.py
│       ├── crud_generation_task.py
│       ├── crud_generated_record.py
│       └── **crud_nft.py**              # 新增：NFT 数据访问
├── frontend/
│   └── web/
│       ├── index.html               # 单页入口（Auth/Generation/Records/NFT 四区块）
│       ├── assets/css/app.css
│       └── js/
│           ├── api.js               # fetch 封装（带 token）
│           ├── auth.js              # 注册/登录
│           ├── generation.js        # 提交任务、查询状态
│           ├── records.js           # 结果列表与预览
│           └── **nft.js**               # 最小 NFT 铸造与查询视图
├── storage/
│   ├── uploads/                     # 用户上传
│   ├── results/                     # 生成结果（图片/视频）
│   └── metadata/                    # 元数据 JSON（tokenURI 用，最小化替代 IPFS）
└── structure.md                     # 本文件（框架说明）
```

---

## 模块职责（只保留完成目标所需的最小集合）
- app/main.py：创建应用、注册 v1 路由；挂载静态目录：
  - `/web` → `frontend/web`（前端）
  - `/files` → `storage/results`（生成媒体访问）
  - `/metadata` → `storage/metadata`（NFT 元数据 JSON 访问）
- api/v1/nft.py：
  - POST `/api/v1/nft/mint`：根据 `record_id` 生成/获取元数据并铸造；返回 `nft_id/token_id/tx_hash/status`。
  - GET  `/api/v1/nft/{id}`：查询 NFT 详情。
- core/config.py（新增链上配置项）：
  - `CHAIN_ENABLED`（bool）、`CHAIN_PROVIDER_URL`、`WALLET_PRIVATE_KEY`、`CONTRACT_ADDRESS`、`CHAIN_NAME`（默认 `sepolia`）。
- models/nft.py（最小字段）：
  - `id`、`record_id`、`chain`、`contract_address`、`token_id`、`tx_hash`、`metadata_uri`、`status`（pending|minted|failed）、`created_at`。
- schemas/nft.py：对应请求/响应模型（`MintRequest{record_id, to_address?}`、`NFTResponse`）。
- services/nft_service.py：
  - `build_metadata(record: GeneratedRecord) -> dict`：最小 JSON（name/description/image 指向 `/files/...`）。
  - `ensure_metadata_file(record_id) -> metadata_uri`：写入 `storage/metadata/nft-<record_id>.json` 并返回 `http://<host>/metadata/nft-<record_id>.json`。
  - `mint_stub(record_id)`：占位模式，生成伪 `tx_hash/token_id`，`status=minted`。
  - `mint_onchain(record_id, to_address?)`：链上模式，使用 web3.py 调用 ERC-721 `mint`/`safeMint(to, tokenURI)`（需配置合约地址与私钥）。
- crud/crud_nft.py：最小 CRUD：`create/get/list/update_status`。

---

## 最小接口设计（含 NFT）
- Auth
  - POST `/api/v1/auth/register`
  - POST `/api/v1/auth/login`（→ JWT）
- Generation
  - POST `/api/v1/generation/tasks`
  - GET  `/api/v1/generation/tasks/{task_id}`
- Records
  - GET  `/api/v1/records`、GET `/api/v1/records/{id}`
- NFT（新增）
  - POST `/api/v1/nft/mint`（body: `record_id`, 可选 `to_address`）
  - GET  `/api/v1/nft/{id}`

---

## 数据模型（最小字段集，含 NFT）
- User：`id`、`email`、`password_hash`、`created_at`
- GenerationTask：`id`、`user_id`、`prompt`、`status`（queued|running|succeeded|failed）、`created_at`、`updated_at`
- GeneratedRecord：`id`、`task_id`、`file_path`、`metadata`、`created_at`
- NFT：`id`、`record_id`、`chain`、`contract_address`、`token_id`、`tx_hash`、`metadata_uri`、`status`、`created_at`

---

## NFT 最精简实现路径（两档可切换）
1) 占位（Stub）模式（默认，零外部依赖即可跑通）
- 在 `mint_stub(record_id)` 中：生成元数据文件并写入 DB 记录，设置 `status=minted`、`tx_hash='stub-<uuid>'`、`token_id=0`。
- 适用：验证流程、联调前端；不上链。

2) 真实链上模式（EVM 测试网，最小依赖）
- 前提：配置 `.env` 中的 `CHAIN_ENABLED=true`、`CHAIN_PROVIDER_URL`（Alchemy/Infura）、`WALLET_PRIVATE_KEY`、`CONTRACT_ADDRESS`（标准 ERC-721，含 `safeMint(to, tokenURI)`）。
- 流程：
  1. 读取 `GeneratedRecord.file_path`，生成 `metadata`（`image` 指向 `/files/...` 的可公开 URL）。
  2. 写入 `storage/metadata/nft-<record_id>.json`，通过 `/metadata` 静态服务暴露为 `metadata_uri`（最小替代 IPFS）。
  3. 用 web3.py 调用合约 `safeMint(to_address or server_address, metadata_uri)`；获取 `tx_hash`、等待回执，解析 `token_id`。
  4. 写入 `NFT` 记录：`status=minted`，保存 `token_id/tx_hash/contract_address/metadata_uri/chain`。
- 备注：生产环境建议将 `metadata` 与媒体文件迁移到 IPFS（nft.storage/Pinata）；此处为“最精简”先用 HTTP 静态资源即可。

---

## 前后端对接（最小方案）
- 静态挂载：
  - `app.mount('/web', StaticFiles(directory='frontend/web', html=True), name='web')`
  - `app.mount('/files', StaticFiles(directory='storage/results'), name='files')`
  - `app.mount('/metadata', StaticFiles(directory='storage/metadata'), name='metadata')`
- 前端 `nft.js`：表单输入 `record_id`（可选 `to_address`），调用 `/api/v1/nft/mint`，展示 `status/tx_hash/token_id`。

---

## 运行与部署（最小化）
- 开发：`uvicorn backend.app.main:app --reload`，访问 `http://localhost:8000/web/`
- 配置：`backend/app/.env`（DB/JWT/存储、可选链上配置）
- 数据库初始化：`SQLAlchemy create_all`

---

## 一致性检查与改造点
- 已存在目录：`backend/app/api/v1`、`core`、`models`、`schemas`、`services`、`utils`、`crud`（多数文件为空，适合按本文补齐）。
- 待新增文件：`api/v1/nft.py`、`models/nft.py`、`schemas/nft.py`、`services/nft_service.py`、`crud/crud_nft.py`、`storage/metadata/`。
- 结论：按本文结构补齐后，NFT 功能可在占位模式立即可用，并可通过配置一键升级到 EVM 测试网真实上链模式，满足“最精简且可实现”的目标。