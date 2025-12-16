import sys
from datetime import datetime, date
from typing import List, Optional
import config


def validate_date(date_str: str) -> Optional[date]:
    """验证日期格式"""
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, config.Config.DATE_FORMAT).date()
    except ValueError:
        print_error(f"invalid date format, use YYYY-MM-DD.")
        return None


def print_table(headers: List[str], rows: List[List[str]]):
    """打印表格"""
    if not rows:
        print("没有数据")
        return

    # 计算每列最大宽度
    col_widths = []
    for i in range(len(headers)):
        max_width = max(
            len(headers[i]),
            max((len(str(row[i])) for row in rows), default=0)
        )
        col_widths.append(max_width + 2)  # 添加一些填充

    # 打印表头
    header_line = "".join(f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers)))
    print(header_line)
    print("-" * len(header_line))

    # 打印数据行
    for row in rows:
        row_line = "".join(f"{str(row[i]):<{col_widths[i]}}" for i in range(len(row)))
        print(row_line)


def print_error(message: str):
    """打印错误信息"""
    if sys.platform.startswith('win'):
        print(f"[Error] {message}")
    else:
        print(f"\033[91m❌ {message}\033[0m")


def print_success(message: str):
    """打印成功信息"""
    if sys.platform.startswith('win'):
        print(f"[Success] {message}")
    else:
        print(f"\033[92m✅ {message}\033[0m")


def print_info(message: str):
    """打印信息"""
    if sys.platform.startswith('win'):
        print(f"[Info] {message}")
    else:
        print(f"\033[94mℹ  {message}\033[0m")


def truncate_text(text: str, max_length: int = 50) -> str:
    """截断文本"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def format_status(status: str) -> str:
    """格式化状态显示"""
    return config.Config.STATUS_MAP.get(status, status)


def format_generation_type(gen_type: str) -> str:
    """格式化生成类型"""
    return config.Config.GENERATION_TYPE_MAP.get(gen_type, gen_type)