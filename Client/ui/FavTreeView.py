import json
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QTreeView, QVBoxLayout, QLabel, QMenu, QMessageBox,
    QInputDialog, QListWidget, QListWidgetItem, QDialog, QPushButton, QHBoxLayout, QLineEdit
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QPixmap
from PySide6.QtCore import Qt, QModelIndex
from ui.RecordDialog import RecordDialog
from ui.HistoryPage import RecordWidget
from services.request_service import async_request

# =====================================================
#   选择收藏项的对话框（提供一个可选文件列表）
# =====================================================


class AliasDialog(QDialog):
    """用于输入别名的对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("输入别名")
        self.resize(250, 120)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("请输入文件别名："))

        self.text_edit = QLineEdit()
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")

        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def get_alias(self):
        return self.text_edit.text().strip()

class FavSelectDialog(QDialog):
    def __init__(self, parent, path_text, items_dict: dict):
        super().__init__(parent)
        self.setWindowTitle("新增收藏")
        self.resize(350, 500)

        self.items_dict = items_dict
        self.selected_result = None   # 将在 accept 时保存最终数据

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"添加路径：{path_text}"))

        # ---- 列表 ----
        self.list = QListWidget()
        self.list.setSpacing(8)

        # 将 QWidget 放入 QListWidget 中
        for url, widget in self.items_dict.items():
            new_record = RecordWidget(widget.get_record_dict())
            new_map = QPixmap(widget.getpixmap())
            new_record.img_label.setPixmap(new_map)
            item = QListWidgetItem(self.list)
            item.setData(Qt.UserRole, url)
            item.setSizeHint(new_record.sizeHint())  # 保证显示正常
            self.list.addItem(item)

            self.list.setItemWidget(item, new_record)

        layout.addWidget(self.list)

        # ---- 按钮 ----
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")

        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        ok_btn.clicked.connect(self._on_ok)
        cancel_btn.clicked.connect(self.reject)

        # 单击列表项 => 弹出别名输入框
        self.list.itemClicked.connect(self._on_item_click)

    # ------------------ 事件处理 ------------------

    def _on_item_click(self, item):
        """用户点击某个 QWidget，则弹出输入别名对话框"""
        url = item.data(Qt.UserRole)

        alias_dlg = AliasDialog(self)
        if alias_dlg.exec() == QDialog.Accepted:
            alias = alias_dlg.get_alias()
            if alias:  # 输入不为空
                self.selected_result = {
                    "alias": alias,
                    "url": url
                }
                self.accept()  # 结束主对话框

    def _on_ok(self):
        """允许用户按确定结束，但必须选中+输入别名"""
        item = self.list.currentItem()
        if not item:
            self.reject()
            return

        url = item.data(Qt.UserRole)

        alias_dlg = AliasDialog(self)
        if alias_dlg.exec() == QDialog.Accepted:
            alias = alias_dlg.get_alias()
            if alias:
                self.selected_result = {
                    "alias": alias,
                    "url": url
                }
                self.accept()

    def get_selected(self):
        """返回用户最终选择的(alias, url, widget)，否则 None"""
        return self.selected_result



# =====================================================
#                 FavTreeView 主类
# =====================================================
class FavTreeView(QWidget):
    def __init__(self, json_data: list | None = None, parent=None):
        super().__init__(parent)

        self.json_data = json_data or []

        # node id 到树具体元组的映射表
        self.node_map = {}

        # 可供“新增收藏”的候选字典，包含url和对应的记录项列表（外部设置）
        self.url_to_available_fav_items = {}


        self.current_folder_id = None

        # —— UI 基础布局 ——
        self.path_label = QLabel()
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.back_button = QPushButton("返回上级")
        self.back_button.clicked.connect(self.__go_up)

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.path_label, alignment=Qt.AlignLeft)
        top_bar.addWidget(self.back_button, alignment=Qt.AlignRight)

        self.empty_label = QLabel("获取收藏夹中...\n\n")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: gray; font-size: 16px;")

        self.tree = QTreeView()
        self.tree.setHeaderHidden(True)
        self.tree.clicked.connect(self.on_left_click)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)

        self.model = QStandardItemModel()
        self.tree.setModel(self.model)

        layout = QVBoxLayout(self)
        layout.addLayout(top_bar)
        layout.addWidget(self.tree)
        layout.addWidget(self.empty_label)

        # 图标
        self.folder_icon = QIcon.fromTheme("folder")
        self.file_icon = QIcon.fromTheme("text-x-generic")
        self.add_folder_icon = QIcon.fromTheme("folder-new")

        self.set_json_tree(self.json_data)

    def __go_up(self):
        if self.current_folder_id is None:
            return
        current = self.node_map[self.current_folder_id]
        if current["parent_id"] is not None:
            self.current_folder_id = current["parent_id"]
            self.refresh_view()

    def __handle_create_new_node_response(self, reply, new_node):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            new_node["id"] = result["data"]["id"]
            self.json_data.append(new_node)
            self.node_map[new_node["id"]] = new_node
            self.refresh_view()


    # =====================================================
    #     外部接口
    # =====================================================
    def set_json_tree(self, json_data: list):
        self.json_data = json_data or []
        self.node_map = {item["id"]: item for item in self.json_data}

        if not self.json_data:
            self.current_folder_id = None
            self.show_empty_view()
        else:
            self.current_folder_id = self.get_root_id()
            self.refresh_view()

    def set_available_fav_items(self, items):
        """设置新增收藏项列表（外部调用）"""
        self.url_to_available_fav_items = items

    def show_error(self, message: str):
        QMessageBox.critical(self, "错误", message)

    def show_info(self, message: str):
        QMessageBox.information(self, "信息", message)

    # =====================================================
    #     空视图控制
    # =====================================================
    def show_empty_view(self):
        self.tree.hide()
        self.path_label.hide()
        self.empty_label.show()
        self.model.clear()

    def show_tree_view(self):
        self.empty_label.hide()
        self.tree.show()
        self.path_label.show()

    # =====================================================
    #     JSON操作
    # =====================================================
    def get_root_id(self):
        for item in self.json_data:
            if item.get("parent_id") is None:
                return item["id"]
        return None

    def get_children(self, parent_id):
        # result = []
        # for n in self.json_data:
        #     if n.get("parent_id") == parent_id:
        #         result.append(n)
        # return result
        return [n for n in self.json_data if n.get("parent_id") == parent_id]

    def get_path(self, node_id):
        path = []
        cur = node_id
        while cur is not None:
            node = self.node_map[cur]
            cur_path = node["name"] if node["name"] != "/" else ""
            path.append(cur_path)
            cur = node["parent_id"]
        if len(path) == 1 and path[0] == "":
            return "/"
        return "/ ".join(reversed(path))

    # =====================================================
    #     UI 列表渲染
    # =====================================================
    def refresh_view(self):
        if not self.json_data or self.current_folder_id is None:
            self.show_empty_view()
            return

        self.show_tree_view()
        self.model.clear()

        # node = self.node_map[self.current_folder_id]
        self.path_label.setText(self.get_path(self.current_folder_id))

        children = self.get_children(self.current_folder_id)

        # —— 新建文件夹项 ——（放在最顶部）
        add_folder_item = QStandardItem("新建文件夹")
        add_folder_item.setIcon(self.add_folder_icon)
        add_folder_item.setData("add_folder", Qt.UserRole)
        self.model.appendRow(add_folder_item)

        # —— 子节点列表 ——
        for n in children:
            item = QStandardItem(n["name"])
            item.setData(n["id"], Qt.UserRole)

            if n["node_type"] == "folder":
                item.setIcon(self.folder_icon)
            else:
                item.setIcon(self.file_icon)
            self.model.appendRow(item)

    # =====================================================
    #     左键行为
    # =====================================================
    def on_left_click(self, index: QModelIndex):
        if not index.isValid():
            return

        data = index.data(Qt.UserRole)
        if data is None:
            return

        # —— 创建文件夹 ——
        if data == "add_folder":
            self.create_new_folder()
            return


        node = self.node_map.get(data)
        if not node:
            return

        if node["node_type"] == "folder":
            self.current_folder_id = node["id"]
            self.refresh_view()
        else:
            self.show_file_detail(node)

    # =====================================================
    #     创建文件夹：点击“新建文件夹”触发
    # =====================================================
    def create_new_folder(self):
        current_path = self.get_path(self.current_folder_id)
        name, ok = QInputDialog.getText(self, "新建文件夹",
                                        f"当前路径：{current_path}\n请输入文件夹名称：")
        if not ok or not name.strip():
            return

        name = name.strip()
        # self.pseudo_id_list.append(temp_id)
        new_node = {
            "id": -1,
            "parent_id": self.current_folder_id,
            "name": name,
            "node_type": "folder"
        }
        async_request(
            sender=self,
            method="POST",
            url="/user/favorite_list",
            data={"parent_id":self.current_folder_id, "name":name, "node_type":"folder"},
            handle_response=lambda reply: self.__handle_create_new_node_response(reply, new_node=new_node)
        )
        # todo 在等待期间为用户提供视觉反馈


    # =====================================================
    #     显示文件详情
    # =====================================================
    def show_file_detail(self, node):
        # info = f"名称：{node['name']}\n文件：{node.get('local_path')}\n"
        # QMessageBox.information(self, "文件详情", info)
        record = self.url_to_available_fav_items.get(node.get("refer_url"))
        if record:
            dlg = RecordDialog({"type":record.type, "prompt":record.prompt, "parameters":record.parameters, "local_path":record.local_path}, self)
            dlg.show()

    # =====================================================
    #     右键菜单
    # =====================================================
    def open_context_menu(self, pos):
        index = self.tree.indexAt(pos)

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #f9f9f9;      /* 浅色背景 */
                color: #000000;                 /* 黑色文字 */
                border: 1px solid #ccc;         /* 边框颜色更浅 */
            }
            QMenu::item {
                padding: 5px 30px;              /* 上下左右内边距 */
            }
            QMenu::item:selected {
                background-color: #d0d0d0;      /* 悬停加深背景色 */
                color: #000000;                  /* 文字仍为黑色 */
            }
        """)



        # —— 情况 A：空白处 → 新增收藏 ——
        if not index.isValid():
            menu.addAction("新增收藏", lambda: self.add_fav_to_folder(self.current_folder_id))
            menu.exec(self.tree.viewport().mapToGlobal(pos))
            return

        node_id = index.data(Qt.UserRole)

        # —— "新建文件夹" 项无右键菜单 ——
        if node_id in ("add_folder", "back"):
            return

        node = self.node_map.get(node_id)

        # —— 情况 B：右键文件夹 → 添加收藏 + 删除 ——
        if node["node_type"] == "folder":
            menu.addAction("在此文件夹新建收藏",
                           lambda: self.add_fav_to_folder(node_id))
            menu.addAction("删除（递归）",
                           lambda: self.delete_node_recursive(node_id))
        else:
            # 文件节点：仅删除
            menu.addAction("删除收藏",
                           lambda: self.delete_node_recursive(node_id))

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # =====================================================
    #     添加收藏项（从列表选取）
    # =====================================================
    def add_fav_to_folder(self, folder_id):
        if not self.url_to_available_fav_items:
            QMessageBox.warning(self, "无可选项目", "没有可添加的收藏项")
            return

        path_text = self.get_path(folder_id)
        dlg = FavSelectDialog(self, path_text, self.url_to_available_fav_items)

        if dlg.exec() != QDialog.Accepted:
            return

        selected = dlg.get_selected()
        if not selected:
            return
        
                # 添加为文件节点
        new_node = {
            "id": 0,  # 临时id，后续由服务器返回真实id
            "parent_id": folder_id,
            "name": selected["alias"],
            "node_type": "file",
            "refer_url": selected["url"]
        }

        async_request(
            sender=self,
            method="POST",
            url="/user/favorite_list",
            data={"parent_id":folder_id, "name":selected["alias"], "node_type":"file", "refer_url":selected["url"]},
            handle_response=lambda reply: self.__handle_create_new_node_response(reply, new_node=new_node)
        )


    # =====================================================
    #     删除节点（递归）
    # =====================================================
    def __handle_delete_node_response(self, reply, node_id):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            to_delete = self.collect_descendants(node_id)
            to_delete.append(node_id)

            self.json_data = [n for n in self.json_data if n["id"] not in to_delete]
            self.node_map = {item["id"]: item for item in self.json_data}

            # 若删除当前目录 → 回到 root 或空视图
            if self.current_folder_id in to_delete:
                self.current_folder_id = self.get_root_id() if self.json_data else None

            self.refresh_view()

    def delete_node_recursive(self, node_id):
        reply = QMessageBox.question(
            self, "确认删除",
            "删除将同时删除所有子节点，确定继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        
        async_request(
            sender=self,
            method="DELETE",
            url=f"/user/favorite_list/{node_id}",
            data=None,
            handle_response=lambda reply: self.__handle_delete_node_response(reply, node_id)
        )


    def collect_descendants(self, node_id):
        result = []
        for child in self.get_children(node_id):
            result.append(child["id"])
            result.extend(self.collect_descendants(child["id"]))
        return result



# =====================================================
# 示例运行
# =====================================================
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    # 初始为空树
    empty_data = []

    app = QApplication(sys.argv)
    w = FavTreeView(empty_data)
    w.resize(400, 500)
    w.show()

    # 模拟数据加载
    w.set_json_tree([
        {"id": 1, "parent_id": None, "name": "/", "node_type": "folder"},
        {"id": 2, "parent_id": 1, "name": "风景图", "node_type": "folder"},
        {"id": 3, "parent_id": 2, "name": "山.png", "node_type": "file"},
    ])

    sys.exit(app.exec())
