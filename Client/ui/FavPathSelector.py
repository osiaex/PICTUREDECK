from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt


class FavPathSelector(QDialog):
    """
    用于选择收藏夹路径的小窗口
    返回：(alias: str, selected_folder_id: int) | None
    """
    def __init__(self, json_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择收藏路径")
        self.resize(300, 300)

        self.json_list = json_list
        self.folder_map = {item["id"]: item for item in json_list if item["node_type"] == "folder"}

        # ------------------ UI ------------------
        layout = QVBoxLayout(self)

        # ---- 别名输入 ----
        layout.addWidget(QLabel("为新的收藏项输入别名："))
        self.alias_edit = QLineEdit()
        layout.addWidget(self.alias_edit)

        # ---- 当前选中的文件夹 ----
        self.current_label = QLabel("当前选择路径：")
        layout.addWidget(self.current_label)

        # ---- 文件夹树 ----
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree)

        # ---- 底部按钮 ----
        bottom = QHBoxLayout()
        self.ok_btn = QPushButton("确认")
        self.cancel_btn = QPushButton("取消")
        bottom.addWidget(self.ok_btn)
        bottom.addWidget(self.cancel_btn)
        layout.addLayout(bottom)

        # ---- 事件 ----
        self.ok_btn.clicked.connect(self.accept_selection)
        self.cancel_btn.clicked.connect(self.reject)
        self.tree.itemSelectionChanged.connect(self.update_current_label)

        # ---- 构造树 ----
        self.build_tree()

        self.selected_folder_id = None

    # ----------------------------------------------------------------------
    def build_tree(self):
        """基于 json 构造树状结构（只包含 folder）"""
        # 构建 children 列表
        children = {fid: [] for fid in self.folder_map}
        root_id = None
        for item in self.folder_map.values():
            pid = item["parent_id"]
            if pid is None:
                root_id = item["id"]
            else:
                if pid in children:
                    children[pid].append(item)

        # 递归构造
        def add_children(parent_item, folder_id):
            for child in children[folder_id]:
                node = QTreeWidgetItem([child["name"]])
                node.setData(0, Qt.UserRole, child["id"])
                parent_item.addChild(node)
                add_children(node, child["id"])

        # root
        root_info = self.folder_map[root_id]
        root_item = QTreeWidgetItem([root_info["name"]])
        root_item.setData(0, Qt.UserRole, root_info["id"])
        self.tree.addTopLevelItem(root_item)

        add_children(root_item, root_id)
        self.tree.expandAll()

    # ----------------------------------------------------------------------
    def update_current_label(self):
        """当用户切换选择时，更新当前路径显示"""
        items = self.tree.selectedItems()
        if not items:
            self.current_label.setText("当前选择路径：")
            self.selected_folder_id = None
            return

        item = items[0]
        fid = item.data(0, Qt.UserRole)

        # 构造路径：向上递归
        path = []
        p = item
        while p:
            path.append(p.text(0))
            p = p.parent()
        path.reverse()
        path_str = "/".join(path)
        if not path_str.startswith("/"):
            path_str = "/" + path_str
        if len(path) != 1:
            # 去掉根目录的重复斜杠
            path_str = path_str.replace("//", "/")
        self.current_label.setText(f"当前选择路径：{path_str}")
        self.selected_folder_id = fid

    # ----------------------------------------------------------------------
    def accept_selection(self):
        alias = self.alias_edit.text().strip()
        if not alias:
            QMessageBox.warning(self, "提示", "别名不能为空")
            return

        if self.selected_folder_id is None:
            QMessageBox.warning(self, "提示", "请先选择一个文件夹")
            return

        self.accept()

    # ----------------------------------------------------------------------
    def get_result(self):
        """若确认，则返回(alias, folder_id)，否则 None"""
        if self.exec() == QDialog.Accepted:
            return self.alias_edit.text().strip(), self.selected_folder_id
        return None


# ======================= 示例调用 =========================
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    json_list = [
        {"id": 1, "parent_id": None, "name": "/", "node_type": "folder"},
        {"id": 2, "parent_id": 1, "name": "images", "node_type": "folder"},
        {"id": 3, "parent_id": 2, "name": "portraits", "node_type": "folder"},
        {"id": 4, "parent_id": 2, "name": "animals", "node_type": "folder"},
        {"id": 5, "parent_id": 1, "name": "docs", "node_type": "folder"},
        # file (ignored)
        {"id": 6, "parent_id": 1, "name": "man.jpg", "node_type": "file"}
    ]

    dlg = FavPathSelector(json_list)
    result = dlg.get_result()
    print("result:", result)

    sys.exit(app.exec())
