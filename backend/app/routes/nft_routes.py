# app/routes/nft_routes.py

import json
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from concurrent.futures import ThreadPoolExecutor
import uuid
from flask import current_app

from ..utils.helpers import api_response
from ..services.nft_service import NFTService
from ..models import db
from ..models import Generation
from ..models import NFT

nft_blueprint = Blueprint("nft", __name__)

nft_service = NFTService()


# 全局线程池，Flask 应用启动时初始化即可
executor = ThreadPoolExecutor(max_workers=4)

# 从task_id到后台任务状态的映射
mint_tasks = {}
transfer_tasks = {}

def run_in_background(func, callback=None, task_id=None, *args, **kwargs):
    """
    在后台执行同步函数，并在完成后执行回调
    func: NFTService 的方法
    callback: 可选，接收 func 返回值的函数
    args, kwargs: 传给 func 的参数
    """
    def task():
        try:
            result = func(*args, **kwargs)
            if callback:
                # 确保回调在主线程中执行，可以用 flask 的 app_context
                callback(result)
        except Exception as e:
            print("后台任务异常:", e)
            if func == nft_service.mint_nft and task_id:
                mint_tasks[task_id] = {"status": "failed", "error": str(e)}
            if func == nft_service.transfer_nft and task_id:
                transfer_tasks[task_id] = {"status": "failed", "error": str(e)}

    executor.submit(task)

# enum('pending_mint','minted','transfer_pending','transferred','failed')

# 后台使用的默认铸造地址
default_address = "0x63107216004a144BA683673562E277267797c6DB"

def parse_mint_result(output):
    """
    解析 mint_nft.mjs 的输出，提取有用信息
    output: mint_nft.mjs 的标准输出字符串
    返回一个字典，包含 tokenId, owner, transactionHash, metadata 等字段
    """
    try:
        data = json.loads(output)
        return {
            "token_id": data.get("tokenId"),
            "owner_address": data.get("owner"),
            "transaction_hash": data.get("transactionHash"),
            "metadata": data.get("metadata"),
        }
    except Exception as e:
        print("解析 mint 结果失败:", e)
        print("原始输出:", output)
        return None

def on_mint_complete(result, mint_task_id, generation_id, current_user_id, app):
    """
    铸造完成后的回调
    result: NFTService.mint_nft 的返回值或异常
    """
    with app.app_context():
        print("Mint complete callback:", result)
        result = result[result.find('{"'):]  # 提取 JSON 部分
        dict_result = parse_mint_result(result) if isinstance(result, str) else None
        if dict_result:
            dict_result["status"] = "minted"
            nft_row = NFT(
                generation_id=generation_id,
                intended_owner_user_id=current_user_id,
                token_id=dict_result.get("token_id"),
                onchain_owner_address=dict_result.get("owner_address"),
                mint_transaction_hash=dict_result.get("transaction_hash"),
                nft_metadata=dict_result.get("metadata"),
                status="minted"
            )
            mint_tasks[mint_task_id] = dict_result
            db.session.add(nft_row)
            db.session.commit()
        
# ---------------------------
# 1. 铸造 NFT
# ---------------------------
@nft_blueprint.route("/mint", methods=["POST"])
@jwt_required()
def mint_nft():
    """
    POST /api/v1/nft/mint
    Request JSON:
    {
        "name": "Cat Picture",
        "description": "A cute cat image",
        "task_id": "uuid-of-generation"
    }
    """
    data = request.get_json() or {}
    name = data.get("name")
    description = data.get("description")
    task_id = data.get("task_id")

    if not all([name, description, task_id]):
        return api_response(code=400, message="缺少必要参数 name/description/task_id")

    current_user_id = int(get_jwt_identity())

    # 1. 查询对应的生成记录
    generation = Generation.query.filter_by(uuid=task_id, user_id=current_user_id).first()
    if not generation:
        return api_response(code=402, message="生成请求不存在或不属于当前用户，无法铸造 NFT")

    if not generation.result_url:
        return api_response(code=403, message="生成结果不存在，无法铸造 NFT")

    image_path = generation.physical_path
    if not image_path:
        return api_response(code=500, message="服务器丢失图片，无法铸造 NFT")

    # 2. 调用 JS 脚本进行 mint
    try:
        app = current_app._get_current_object()
        mint_task_id = uuid.uuid4().hex
        run_in_background(
            nft_service.mint_nft, 
            lambda r: on_mint_complete(r, mint_task_id, generation.id, current_user_id, app), 
            task_id=mint_task_id,
            name=name, 
            description=description, 
            image_path=image_path
        )
        dict_result = {"status": "pending"}
        mint_tasks[mint_task_id] = dict_result
    except Exception as e:
        print("Mint NFT error:", e)
        return api_response(code=500, message="NFT 铸造失败", data={"error": str(e)})

    return api_response(code=200, message="NFT 铸造请求已提交，正在后台处理", data={"mint_task_id": mint_task_id})


@nft_blueprint.route("/mint/<string:mint_task_id>", methods=["GET"])
@jwt_required()
def get_mint_status(mint_task_id):
    """
    GET /api/v1/nft/mint/<mint_task_id>
    查询铸造任务状态
    """
    current_user_id = int(get_jwt_identity())

    if mint_task_id not in mint_tasks:
        return api_response(code=404, message="铸造任务不存在")

    result = mint_tasks[mint_task_id]
    if result.get("status") == "failed":
        return api_response(code=500, message="铸造任务失败", data=result)
    if result.get("status") == "pending":
        return api_response(code=202, message="铸造任务处理中", data=result)
    if result.get("status") == "minted":
        mint_tasks.pop(mint_task_id)
        return api_response(code=200, message="铸造任务已完成", data=result)
# ---------------------------
# 2. 转移 NFT
# ---------------------------

def on_transfer_complete(result, transfer_task_id, token_id, to_address, app):
    with app.app_context():
        print("Transfer complete callback:", result)

        if "successful" in str(result).lower():
            transfer_tasks[transfer_task_id] = {
                "status": "transferred",
                "token_id": token_id,
                "to_address": to_address
            }

            nft = (
                db.session.execute(
                    db.select(NFT).where(NFT.token_id == str(token_id))
                )
                .scalars()
                .first()
            )

            if not nft:
                app.logger.error("NFT not found for token_id=%s", token_id)
                return

            nft.status = "transferred"
            nft.onchain_owner_address = to_address
            db.session.commit()

        else:
            transfer_tasks[transfer_task_id] = {
                "status": "failed",
                "error": str(result)
            }


@nft_blueprint.route("/transfer", methods=["POST"])
@jwt_required()
def transfer_nft():
    """
    POST /api/v1/nft/transfer

    Request JSON:
    {
        "token_id": "1",
        "to_address": "0xUserWalletAddress"
    }
    """
    data = request.get_json() or {}
    token_id = data.get("token_id")
    to_address = data.get("to_address")

    if not token_id or not to_address:
        return api_response(code=400, message="缺少 token_id 或 to_address")

    current_user_id = int(get_jwt_identity())

    # 1. 查询数据库 NFT
    nft = NFT.query.filter_by(token_id=str(token_id)).first()
    if not nft:
        return api_response(code=404, message="未找到对应 NFT 记录")

    # 2. 权限检查：用户必须是当前记录的 owner_user_id
    if nft.intended_owner_user_id != current_user_id:
        return api_response(code=402, message="您不是该 NFT 的拥有者，无权转移")

    # 3. 调用 JS 脚本执行转移
    try:
        transfer_task_id = uuid.uuid4().hex
        dict_result = {"status": "transfer_pending"}
        transfer_tasks[transfer_task_id] = dict_result
        app = current_app._get_current_object()
        run_in_background(nft_service.transfer_nft, lambda r: on_transfer_complete(r, transfer_task_id, token_id, to_address, app),
            task_id=transfer_task_id,
            token_id=nft.token_id,
            to_address=to_address,
            amount=1
        )
    except Exception as e:
        print("Transfer NFT error:", e)
        return api_response(code=500, message="NFT 转移请求失败", data={"error": str(e)})

    # 4. 更新数据库（状态 transfer_pending，等待链上确认）
    memory_address_hex = hex(id(nft))
    print(f"Hex memory address: {memory_address_hex}")
    nft.status = "transfer_pending"
    db.session.commit()

    return api_response(code=200, message="NFT 转移请求已提交", data={"transfer_task_id": transfer_task_id})

@nft_blueprint.route("/transfer/<string:transfer_task_id>", methods=["GET"])
@jwt_required()
def get_transfer_status(transfer_task_id):
    """
    GET /api/v1/nft/transfer/<transfer_task_id>
    查询转移任务状态
    """
    current_user_id = int(get_jwt_identity())

    if transfer_task_id not in transfer_tasks:
        return api_response(code=404, message="转移任务不存在")

    result = transfer_tasks[transfer_task_id]
    if result.get("status") == "failed":
        return api_response(code=500, message="转移任务失败", data=result)
    if result.get("status") == "transfer_pending":
        return api_response(code=202, message="转移任务处理中", data=result)
    if result.get("status") == "transferred":
        transfer_tasks.pop(transfer_task_id)
        return api_response(code=200, message="转移任务已完成", data=result)