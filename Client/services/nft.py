import json
from PySide6.QtWidgets import QInputDialog
from PySide6.QtCore import QTimer

from services.request_service import async_request

def mint_nft(sender_window, widget):
    task_id = widget.task_id   # 你已经有 task_id
    if not widget.result_url:
        sender_window.show_error("无效的生成结果，无法铸造 NFT。")
        return
    # 输入 NFT 名称
    name, ok = QInputDialog.getText(sender_window, "NFT 名称", "请输入 NFT 名称：")
    if not ok or not name.strip():
        return

    # 输入 NFT 描述（多行）
    description, ok = QInputDialog.getMultiLineText(
        sender_window, "NFT 描述", "请输入描述："
    )
    if not ok:
        return

    # 构造请求体
    data = {
        "name": name.strip(),
        "description": description.strip(),
        "task_id": task_id,
    }

    def __on_mint_response(reply, widget):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") != 200:
            sender_window.show_error(result.get("message", "上链失败"))
            return
        sender_window.show_info(result.get("message", "开始上链"))
        mint_task_id = result.get("data", {}).get("mint_task_id", "")
        
        def on_chain_status_update(reply, timer: QTimer):
            response_data = reply.readAll().data().decode("utf-8")
            result = json.loads(response_data)
            status = result.get("data", {}).get("status", "")
            if status == "minted":
                timer.stop()
                widget.nft_token_id = result.get("data", {}).get("token_id", "")
                widget.update_status(is_chain_pending=False, is_on_chain=True)
                sender_window.show_info("NFT 上链成功！")

            elif status == "failed":
                timer.stop()
                sender_window.show_error("NFT 上链失败！")
            else:
                print("NFT 上链中，状态：", status)

        def poll_chain_status(timer: QTimer):
            async_request(
                sender=sender_window,
                method="GET",
                url=f"/nft/mint/{mint_task_id}",
                data=None,
                handle_response=lambda reply: on_chain_status_update(reply, timer)
            )

        timer = QTimer(sender_window)
        timer.timeout.connect(lambda: poll_chain_status(timer))
        timer.start(5000)  # 每5秒轮询一次
        poll_chain_status(timer)  # 立即执行一次


    async_request(
        sender=sender_window,
        method="POST",
        url="/nft/mint",
        data=data,
        handle_response=lambda reply: __on_mint_response(reply, widget)
    )
    widget.update_status(is_chain_pending=True)


def transfer_nft(sender_window, widget):
    # 转让 NFT 的逻辑
    token_id = widget.nft_token_id
    if not token_id:
        sender_window.show_error("无效的 NFT Token ID，无法转让。")
        return
    to_address, ok = QInputDialog.getText(sender_window, "转让 NFT", "请输入接收方地址：")
    if not ok or not to_address.strip():
        return
    data = {
        "token_id": token_id,
        "to_address": to_address.strip(),
    }

    def __on_transfer_response(reply):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") != 200:
            sender_window.show_error(result.get("message", "转让失败"))
            return
        sender_window.show_info(result.get("message", "NFT 转移请求已提交"))
        transfer_task_id = result.get("data", {}).get("transfer_task_id", "")

        def on_transfer_status_update(reply, timer: QTimer):
            response_data = reply.readAll().data().decode("utf-8")
            result = json.loads(response_data)
            status = result.get("data", {}).get("status", "")
            if status == "transferred":
                timer.stop()
                widget.update_status(is_transfer_pending=False, is_transferred=True)
                sender_window.show_info("NFT 转让成功！")
            elif status == "failed":
                timer.stop()
                sender_window.show_error("NFT 转让失败！")
            else:
                print("NFT 转让中，状态：", status)

        def poll_transfer_status(timer: QTimer):
            async_request(
                sender=sender_window,
                method="GET",
                url=f"/nft/transfer/{transfer_task_id}",
                data=None,
                handle_response=lambda reply: on_transfer_status_update(reply, timer)
            )

        timer = QTimer(sender_window)
        timer.timeout.connect(lambda: poll_transfer_status(timer))
        timer.start(5000)  # 每5秒轮询一次
        poll_transfer_status(timer)  # 立即执行一次

    async_request(
        sender=sender_window,
        method="POST",
        url="/nft/transfer",
        data=data,
        handle_response=__on_transfer_response
    )
    widget.update_status(is_transfer_pending=True)