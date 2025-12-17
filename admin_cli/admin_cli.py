from utils import validate_date, print_table, print_error, print_success, print_info, truncate_text, format_status, \
    format_generation_type
import cmd
import os
import getpass
from typing import Optional, Dict, Any
from database import get_db, AdminService, AuthService

class AdminCLI(cmd.Cmd):
    """PICTCTUREDECK 后台管理系统 - 带认证版本"""

    intro = """
╔══════════════════════════════════════════════════════════════╗
║                       PICTCTUREDECK                          ║
║                        后台管理系统                            ║
╚══════════════════════════════════════════════════════════════╝

输入 'login' 登录系统，或 'help' 查看帮助
    """

    prompt = "Not logged in>"

    def __init__(self):
        super().__init__()
        self.db_session = None
        self.admin_service = None
        self.auth_service = None
        self.current_user = None
        self.session_token = None
        self.setup_database()

    def setup_database(self):
        """初始化数据库连接"""
        try:
            from database import init_db, test_connection
            init_db()
            if test_connection():
                self.db_session = next(get_db())
                self.admin_service = AdminService(self.db_session)
                self.auth_service = AuthService(self.db_session)
                print_success("✅ Database connection successful!")
            else:
                print_error("❌ Database connection failed!")
        except Exception as e:
            print_error(f"❌ An error occurred while initializing the database: {e}")

    # ========== 认证装饰器 ==========
    def login_required(func):
        """登录验证装饰器"""

        def wrapper(self, *args, **kwargs):
            if not self.is_authenticated():
                print_error("❌ This command requires login to execute.")
                print("Please use the 'login' command to log in to the system.")
                return None
            return func(self, *args, **kwargs)

        return wrapper

    def is_authenticated(self) -> bool:
        """检查当前是否已认证登录"""
        if not self.session_token or not self.current_user:
            return False

        # 验证会话有效性
        try:
            if self.auth_service and self.auth_service.validate_session(self.session_token):
                return True
            else:
                # 会话无效，清理状态
                self.current_user = None
                self.session_token = None
                self.update_prompt()
                return False
        except Exception:
            return False

    def update_prompt(self):
        """更新命令提示符显示当前用户"""
        if self.current_user:
            self.prompt = f"{self.current_user}> "
        else:
            self.prompt = "Not logged in> "

    def do_login(self, arg):
        """
        登录系统
        用法: login
        示例:
          login
        """
        if self.is_authenticated():
            print_info("You are currently logged in. If you need to log in again, please first execute 'logout' to exit.")
            return

        print("\n" + "=" * 50)
        print("             Log in as administrator")
        print("=" * 50)

        try:
            print("Please enter your username：")
            name = input()
            if not name:
                print_error("❌ Username cannot be empty.")
                return

            print("Please enter your password：")
            password = getpass.getpass()
            if not password:
                print_error("❌ Password cannot be empty.")
                return

            # 调用认证服务
            auth_result = self.auth_service.authenticate_admin(
                username=name,
                password=password,
                ip_address="127.0.0.1"  # 本地访问
            )

            # 登录成功，更新状态
            self.session_token = auth_result["session_token"]
            self.current_user = auth_result["username"]
            self.update_prompt()

            print_success(f"Login successful! Welcome,{self.current_user}!")
            print_info(f"Login time: {auth_result['login_time'].strftime('%Y-%m-%d %H:%M:%S')}")

        except ValueError as e:
            print_error(f"❌ Login failed: {str(e)}")
        except Exception as e:
            print_error(f"❌ Login failed with an error: {e}")

    def do_logout(self, arg):
        """
        退出当前登录的账户
        用法: logout
        """
        if not self.is_authenticated():
            print_info("❌ You are currently not logged in.")
            return

        try:
            if self.auth_service:
                self.auth_service.logout(self.session_token)

            username = self.current_user
            self.current_user = None
            self.session_token = None
            self.update_prompt()

            print_success(f"Goodbye, {username}! You have logged out securely.")
        except Exception as e:
            print_error(f"❌ Error logging out: {e}")
            # 强制清理状态
            self.current_user = None
            self.session_token = None
            self.update_prompt()

    def do_help(self, arg):
        """
        显示帮助信息
        用法: help [命令名]
        示例:
          help          # 显示所有可用命令
          help login    # 显示login命令的详细帮助
        """
        if arg:
            # 显示特定命令的详细帮助
            command_help = self.get_command_help(arg)
            if command_help:
                print(f"\n{arg} 命令帮助:")
                print("=" * 50)
                print(command_help)
            else:
                print(f"❌ 未知命令: {arg}")
                print("💡 输入 'help' 查看所有可用命令")
        else:
            # 显示完整的帮助菜单
            self.show_complete_help()

    def show_complete_help(self):
        """显示完整的帮助菜单"""
        print("\n" + "=" * 60)
        print("              PICTCTUREDECK 后台管理系统帮助")
        print("=" * 60)

        # 认证命令
        print("\n🔐 认证命令:")
        print("-" * 40)
        self.print_command_help("login", "登录系统")
        self.print_command_help("logout", "退出当前登录")
        self.print_command_help("passwd", "修改当前用户密码")

        # 用户管理命令
        print("\n👥 用户管理命令:")
        print("-" * 40)
        self.print_command_help("ban", "封禁用户: ban <用户ID>")
        self.print_command_help("unban", "解封用户: unban <用户ID>")
        self.print_command_help("user_list", "列出用户: user_list [--banned|--active]")

        # 统计查询命令
        print("\n📊 统计查询命令:")
        print("-" * 40)
        self.print_command_help("stats", "生成记录统计: stats [--from 日期] [--to 日期]")
        self.print_command_help("illegal_stats", "违规统计: illegal_stats <task|user> [--from 日期] [--to 日期]")

        # 系统命令
        print("\n⚙️ 系统命令:")
        print("-" * 40)
        self.print_command_help("clear", "清屏")
        self.print_command_help("help", "显示帮助信息")
        self.print_command_help("exit", "退出系统")
        self.print_command_help("quit", "退出系统")

        # 使用示例
        print("\n💡 使用示例:")
        print("-" * 40)
        print("  登录系统: login")
        print("  封禁用户: ban 1")
        print("  查看统计: stats --from 2025-12-01 --to 2025-12-10")
        print("  违规统计: illegal_stats task --from 2025-12-01")
        print("  用户列表: user_list --banned")

        # 注意事项
        print("\n⚠️ 注意事项:")
        print("-" * 40)
        print("  • 所有管理命令需要登录后才能使用")
        print("  • 日期格式: YYYY-MM-DD (例如: 2025-12-01)")
        print("  • 使用 'help <命令名>' 查看具体命令的详细用法")

        print("\n" + "=" * 60)

    def print_command_help(self, command, description):
        """格式化输出命令帮助信息"""
        print(f"  {command:<15} {description}")

    def get_command_help(self, command_name):
        """获取特定命令的详细帮助信息"""
        help_texts = {
            "login": """
    登录系统
    用法: login

    系统会提示您输入用户名和密码。
    成功登录后即可使用所有管理功能。

    示例:
      login
      然后按照提示输入用户名和密码
            """,

            "logout": """
    退出当前登录的账户
    用法: logout

    这将清除当前会话并返回到未登录状态。
            """,

            "passwd": """
    修改当前登录用户的密码
    用法: passwd

    系统会提示您输入当前密码和新密码。
    新密码需要输入两次以确认。

    安全要求:
      • 新密码长度至少6位
      • 建议使用字母、数字和特殊字符组合
            """,

            "whoami": """
    显示当前登录用户信息
    用法: whoami

    显示当前会话的用户名、登录时间和会话状态。
            """,

            "ban": """
    封禁用户
    用法: ban <用户ID>

    参数:
      <用户ID> - 要封禁的用户ID

    示例:
      ban 1     # 封禁用户ID为1的用户
      ban 3     # 封禁用户ID为3的用户

            """,

            "unban": """
    解封用户
    用法: unban <用户ID>

    参数:
      <用户ID> - 要解封的用户ID

    示例:
      unban 1   # 解封用户ID为1的用户
            """,

            "user_list": """
    列出用户
    用法: user_list [选项]

    选项:
      --banned    # 只显示被封禁的用户
      --active    # 只显示活跃用户
      无选项      # 显示所有用户

    示例:
      user_list           # 显示所有用户
      user_list --banned  # 只显示被封禁的用户
      user_list --active  # 只显示活跃用户
            """,

            "stats": """
    生成记录统计
    用法: stats [选项]

    选项:
      --from <日期>  # 开始日期 (格式: YYYY-MM-DD)
      --to <日期>    # 结束日期 (格式: YYYY-MM-DD)

    示例:
      stats                      # 显示所有生成记录
      stats --from 2025-12-01    # 错误: 需要同时指定结束日期
      stats --to 2025-12-10      # 错误: 需要同时指定开始日期
      stats --from 2025-12-01 --to 2025-12-10  # 显示指定时间段的记录

    注意: 必须同时提供开始日期和结束日期，或者都不提供。
            """,

            "illegal_stats": """
    违规统计
    用法: illegal_stats <类型> [选项]

    参数:
      <类型> - 统计类型，必须是 'task' 或 'user'
        • task - 按任务统计违规内容
        • user - 按用户统计违规次数

    选项:
      --from <日期>  # 开始日期 (格式: YYYY-MM-DD)
      --to <日期>    # 结束日期 (格式: YYYY-MM-DD)

    示例:
      illegal_stats task                  # 统计所有违规任务
      illegal_stats user                  # 统计用户违规次数
      illegal_stats task --from 2025-12-01 --to 2025-12-10  # 统计指定时间段的违规任务
            """,

            "system_stats": """
    系统统计信息
    用法: system_stats

    显示系统总体统计信息，包括:
      • 用户统计: 总用户数、活跃用户、封禁用户
      • 任务统计: 总任务数、已完成、失败、今日任务
      • 违规统计: 总违规次数

    无需参数，直接显示当前系统状态。
            """,

            "clear": """
    清屏
    用法: clear

    清除终端屏幕，保持界面整洁。
            """,

            "exit": """
    退出系统
    用法: exit

    安全退出PICTCTUREDECK后台管理系统。
    如果当前已登录，会自动执行logout操作。
            """,

            "quit": """
    退出系统 (exit的别名)
    用法: quit

    功能与exit命令完全相同，提供多种退出方式。
            """
        }

        return help_texts.get(command_name)

    def show_quick_help(self):
        """显示快速帮助（简洁版）"""
        print("\n📋 快速命令参考:")
        print("=" * 40)
        commands = [
            ("login", "登录系统"),
            ("logout", "退出登录"),
            ("ban <ID>", "封禁用户"),
            ("unban <ID>", "解封用户"),
            ("user_list", "列出用户"),
            ("stats", "生成记录统计"),
            ("illegal_stats", "违规统计"),
            ("system_stats", "系统统计"),
            ("help", "显示帮助"),
            ("exit/quit", "退出系统")
        ]

        for cmd, desc in commands:
            print(f"  {cmd:<20} {desc}")

        print("\n💡 提示: 使用 'help <命令名>' 查看详细用法")

    @login_required
    def do_passwd(self, arg):
        """
        修改当前登录用户的密码
        用法: passwd
        示例:
          passwd
        """
        try:
            print("\n" + "=" * 50)
            print("                  Change password")
            print("=" * 50)

            old_password = getpass.getpass("Current password: ")
            new_password = getpass.getpass("New password: ")
            confirm_password = getpass.getpass("Confirm new password: ")

            if not old_password or not new_password:
                print_error("❌ Password cannot be empty!")
                return

            if new_password != confirm_password:
                print_error("❌ The new passwords you entered do not match.")
                return

            # 获取当前用户ID
            user_info = self.auth_service.get_session_user(self.session_token)
            if not user_info:
                print_error("❌ Unable to retrieve user information. Please log in again.")
                return

            # 修改密码
            success = self.auth_service.change_password(
                user_id=user_info["user_id"],
                old_password=old_password,
                new_password=new_password
            )

            if success:
                print_success("✅ Password changed successfully!")
            else:
                print_error("❌ Failed to change password.")

        except ValueError as e:
            print_error(f"❌ {str(e)}")
        except Exception as e:
            print_error(f"❌ An error occurred while changing the password: {e}")

    @login_required
    def do_ban(self, arg):
        """封禁用户: ban <用户ID>"""
        if not arg:
            print_error("❌ Please provide a user ID, for example: ban 1")
            return

        try:
            user_id = int(arg.strip())
            success = self.admin_service.ban_user(user_id)
            if success:
                print_success(f"✅ User {user_id} banned.")
        except ValueError as e:
            print_error(f"❌ {str(e)}")
        except Exception as e:
            print_error(f"❌ 执行命令时出错: {e}")

    @login_required
    def do_unban(self, arg):
        """解封用户: unban <用户ID>"""
        if not arg:
            print_error("❌ Please provide a user ID, for example: unban 1")
            return

        try:
            user_id = int(arg.strip())
            success = self.admin_service.unban_user(user_id)
            if success:
                print_success(f"✅ User {user_id} unbanned.")
        except ValueError as e:
            print_error(f"❌ {str(e)}")
        except Exception as e:
            print_error(f"❌ 执行命令时出错: {e}")

    @login_required
    def do_user_list(self, arg):
        """列出用户: user_list [--banned|--active]"""
        try:
            banned_only = '--banned' in arg
            active_only = '--active' in arg

            users = self.admin_service.get_users(
                banned_only=banned_only,
                active_only=active_only
            )

            headers = ["ID", "Username", "Email", "Status"]
            rows = []
            for user in users:
                rows.append([
                    str(user.id),
                    user.username,
                    user.email,
                    "banned" if user.status == "banned" else "active",
                ])

            status_text = "封禁" if banned_only else "活跃" if active_only else "所有"
            print_info(f"👥 找到 {len(users)} 个{status_text}用户")
            print_table(headers, rows)

        except Exception as e:
            print_error(f"❌ 执行命令时出错: {e}")

    @login_required
    def do_stats(self, arg):
        """生成记录统计: stats [--from 日期] [--to 日期]"""
        args = self.parse_args(arg)

        from_date = None
        to_date = None
        if '--from' in args:
            from_date = self.validate_date(args['--from'])
            if from_date is None:  # 有值但验证失败
                return
        if '--to' in args:
            to_date = self.validate_date(args['--to'])
            if to_date is None:  # 有值但验证失败
                return

        try:
            tasks = self.admin_service.get_generation_stats(
                start_date=from_date,
                end_date=to_date
            )

            headers = ["ID", "user_id", "prompt","type ", "status", "created_at"]
            rows = []
            for task in tasks:
                rows.append([
                    str(task.id),
                    str(task.user_id),
                    self.truncate_text(task.prompt or "", 30),
                    self.format_generation_type(task.generation_type),
                    self.format_status(task.status),
                    task.created_at.strftime("%Y-%m-%d %H:%M")
                ])

            date_range = ""
            if from_date and to_date:
                date_range = f" ({from_date} 到 {to_date})"
            print_info(f"Found {len(tasks)} generation record(s) {date_range}")
            print_table(headers, rows)

        except ValueError as e:
            print_error(f"❌ {str(e)}")
        except Exception as e:
            print_error(f"❌ 执行命令时出错: {e}")

    @login_required
    def do_illegal_stats(self, arg):
        """违规统计: illegal_stats <task|user> [--from 日期] [--to 日期]"""
        args = self.parse_args(arg)

        if not args or 'type' not in args:
            print_error("❌ 请指定统计类型: illegal_stats <task|user> [--from 日期] [--to 日期]")
            return

        stats_type = args['type']
        from_date = self.validate_date(args.get('--from')) if '--from' in args else None
        to_date = self.validate_date(args.get('--to')) if '--to' in args else None

        try:
            stats = self.admin_service.get_illegal_stats(
                stats_type=stats_type,
                start_date=from_date,
                end_date=to_date
            )

            if stats_type == "task":
                headers = ["ID", "user_id", "prompt", "review_message", "created_at"]
                rows = []

                for task in stats["violation_tasks"]:
                    # # 生成review_message
                    # if task.prompt:
                    #     prompt_lower = task.prompt.lower()
                    #     if "暴露" in prompt_lower or "色情" in prompt_lower:
                    #         review_msg = "色情内容"
                    #     elif "暴力" in prompt_lower:
                    #         review_msg = "暴力内容"
                    #     elif "违法" in prompt_lower or "不当" in prompt_lower:
                    #         review_msg = "违法内容"
                    #     else:
                    #         review_msg = "不当内容"
                    # else:
                    #     review_msg = "无提示词"

                    created_at_str = task.created_at.strftime("%Y-%m-%dT%H:%M:%S+ 08:00")

                    rows.append([
                        str(task.id),
                        str(task.user_id),
                        task.prompt or "",
                        task.parameters['review']['message'] if task.parameters and 'review' in task.parameters and 'message' in task.parameters['review'] else "",
                        created_at_str
                    ])

                print_info(f"Found {stats['total_count']} violation records.")
                print_table(headers, rows)

            elif stats_type == "user":
                headers = ["用户ID", "用户名", "违规次数"]
                rows = []
                for user_stats in stats["user_violations"]:
                    rows.append([
                        str(user_stats["user_id"]),
                        user_stats["username"],
                        str(user_stats["violation_count"])
                    ])

                print_info(f"Found {stats['total_count']} violation records.")
                print_table(headers, rows)

        except ValueError as e:
            print_error(f"❌ {str(e)}")
        except Exception as e:
            print_error(f"❌ 执行命令时出错: {e}")

    @login_required
    def do_system_stats(self, arg):
        """系统统计信息: system_stats"""
        try:
            stats = self.admin_service.get_system_stats()

            print_info("📊 系统统计信息")
            print("=" * 50)
            print(f"总用户数: {stats['total_users']}")
            print(f"活跃用户: {stats['active_users']}")
            print(f"封禁用户: {stats['banned_users']}")
            print(f"总生成任务: {stats['total_tasks']}")
            print(f"今日任务: {stats['today_tasks']}")
            print("=" * 50)

        except Exception as e:
            print_error(f"❌ 获取系统统计时出错: {e}")

    # ========== 辅助方法 ==========
    def validate_date(self, date_str: str):
        """验证日期格式的辅助方法"""
        from utils import validate_date
        return validate_date(date_str)

    def format_status(self, status: str) -> str:
        """格式化状态显示"""
        status_map = {
            'active': '活跃',
            'banned': '已封禁',
            'completed': '已完成',
            'failed': '失败'
        }
        return status_map.get(status, status)

    def format_generation_type(self, gen_type: str) -> str:
        """格式化生成类型"""
        type_map = {
            't2i': '文生图',
            'i2i': '图生图',
            't2v': '文生视频'
        }
        return type_map.get(gen_type, gen_type)

    def truncate_text(self, text: str, max_length: int) -> str:
        """截断长文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def parse_args(self, arg_line: str) -> Dict[str, Any]:
        """解析命令行参数"""
        # 您原有的参数解析逻辑
        args = {}
        if not arg_line:
            return args

        parts = arg_line.split()
        i = 0
        while i < len(parts):
            if parts[i].startswith('--'):
                if i + 1 < len(parts) and not parts[i + 1].startswith('--'):
                    args[parts[i]] = parts[i + 1]
                    i += 2
                else:
                    args[parts[i]] = True
                    i += 1
            else:
                if 'type' not in args:
                    args['type'] = parts[i]
                i += 1

        return args

    # ========== 系统命令 ==========
    def do_clear(self, arg):
        """清屏: clear"""
        os.system('cls' if os.name == 'nt' else 'clear')
        if self.is_authenticated():
            print_success(f"✅ 已清屏，欢迎回来 {self.current_user}!")

    def do_exit(self, arg):
        """退出系统: exit"""
        if self.is_authenticated():
            self.do_logout(arg)
        print_info("感谢使用，再见！")
        if self.db_session:
            self.db_session.close()
        return True

    def do_quit(self, arg):
        """退出系统: quit"""
        return self.do_exit(arg)

    def emptyline(self):
        """空行处理 - 不执行任何操作"""
        pass

    def default(self, line):
        """处理未知命令"""
        print_error(f"❌ 未知命令: {line}")
        print("💡 输入 'help' 查看可用命令")

    def precmd(self, line):
        """在每个命令执行前调用 - 用于会话心跳"""
        if self.is_authenticated() and self.auth_service:
            try:
                # 更新会话活动时间
                self.auth_service.validate_session(self.session_token)
            except Exception:
                # 会话失效，自动登出
                self.current_user = None
                self.session_token = None
                self.update_prompt()
                print_error("❌ 会话已过期，请重新登录")
        return line


if __name__ == "__main__":
    try:
        cli = AdminCLI()
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print_error(f"❌ 系统严重错误: {e}")
        print("程序即将退出...")

    def preloop(self):
        """在循环开始前执行"""
        print_info("系统初始化完成，请输入命令开始使用...")

    def postcmd(self, stop, line):
        """在每个命令后执行"""
        if not stop:
            print()  # 添加空行使界面更清晰
        return stop

    def emptyline(self):
        """空行处理 - 不执行任何操作"""
        pass

    def do_exit(self, arg):
        """退出系统: exit"""
        print_info("感谢使用 PICTCTUREDECK 后台管理系统!")
        if self.db_session:
            self.db_session.close()
        return True

    def do_quit(self, arg):
        """退出系统: quit"""
        return self.do_exit(arg)

    def do_clear(self, arg):
        """清屏: clear"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print(self.intro)

    # 用户管理命令
    def do_ban(self, arg):
        """封禁用户: ban <用户ID>"""
        if not arg:
            print_error("❌ 请提供用户ID，例如: ban 1")
            return

        try:
            user_id = int(arg.strip())
            self.admin_service.ban_user(user_id)
            print_success(f"✅ User {user_id} banned")
        except ValueError as e:
            print_error(f"❌ {str(e)}")
        except Exception as e:
            print_error(f"❌ 执行命令时出错: {e}")

    def do_unban(self, arg):
        """解封用户: unban <用户ID>"""
        if not arg:
            print_error("❌ 请提供用户ID，例如: unban 1")
            return

        try:
            user_id = int(arg.strip())
            self.admin_service.unban_user(user_id)
            print_success(f"✅ User {user_id} unbanned.")
        except ValueError as e:
            print_error(f"❌ {str(e)}")
        except Exception as e:
            print_error(f"❌ 执行命令时出错: {e}")

    def do_user_list(self, arg):
        """列出用户: user_list [--banned|--active]"""
        args = arg.split()
        banned_only = '--banned' in args
        active_only = '--active' in args

        try:
            users = self.admin_service.get_users(banned_only=banned_only, active_only=active_only)

            headers = ["ID", "Username", "Email", "Status"]
            rows = []
            for user in users:
                rows.append([
                    str(user.id),
                    user.username,
                    truncate_text(user.email, 20),
                    format_status(user.status)
                ])

            status_text = "已封禁" if banned_only else "活跃" if active_only else "所有"
            print_info(f"找到 {len(users)} 个{status_text}用户")
            print_table(headers, rows)

        except Exception as e:
            print_error(f"❌ 执行命令时出错: {e}")

    # 统计命令
    def do_stats(self, arg):
        """生成记录统计: stats [--from 日期] [--to 日期]"""
        args = self.parse_args(arg)
        from_date = validate_date(args.get('--from')) if '--from' in args else None
        to_date = validate_date(args.get('--to')) if '--to' in args else None

        try:
            tasks = self.admin_service.get_generation_stats(start_date=from_date, end_date=to_date)

            headers = ["ID", "用户ID", "类型", "提示词", "状态", "创建时间"]
            rows = []
            for task in tasks:
                rows.append([
                    str(task.id),
                    str(task.user_id),
                    format_generation_type(task.generation_type),
                    truncate_text(task.prompt or "", 30),
                    format_status(task.status),
                    task.created_at.strftime("%Y-%m-%d %H:%M")
                ])

            date_range = ""
            if from_date and to_date:
                date_range = f" ({from_date} 到 {to_date})"
            print_info(f"找到 {len(tasks)} 条生成记录{date_range}")
            print_table(headers, rows)

        except ValueError as e:
            print_error(f"❌ {str(e)}")
        except Exception as e:
            print_error(f"❌ 执行命令时出错: {e}")

    def do_illegal_stats(self, arg):
        """违规统计: illegal_stats <task|user> [--from 日期] [--to 日期]"""
        # 初始化所有变量
        from_date = None
        to_date = None
        args = {}

        try:
            # 解析参数
            args = self.parse_args(arg)

            if not args or 'type' not in args:
                print_error("❌ 请指定统计类型: illegal_stats <task|user> [--from 日期] [--to 日期]")
                return

            stats_type = args['type']

            # 安全地获取日期参数
            if '--from' in args:
                from_date = validate_date(args['--from'])
                if from_date is None and args['--from']:
                    return

            if '--to' in args:
                to_date = validate_date(args['--to'])
                if to_date is None and args['--to']:
                    return

            # 调用服务方法
            stats = self.admin_service.get_illegal_stats(
                stats_type=stats_type,
                start_date=from_date,
                end_date=to_date
            )

            if stats_type == "task":
                # 违规任务统计
                headers = ["ID", "user_id", "prompt", "review_message", "created_at"]
                rows = []

                for task in stats["violation_tasks"]:
                    # 生成review_message
                    if task.prompt:
                        prompt_lower = task.prompt.lower()
                        if "暴露" in prompt_lower or "色情" in prompt_lower:
                            review_msg = "色情内容"
                        elif "暴力" in prompt_lower:
                            review_msg = "暴力内容"
                        elif "违法" in prompt_lower or "不当" in prompt_lower:
                            review_msg = "违法内容"
                        else:
                            review_msg = "不当内容"
                    else:
                        review_msg = "无提示词"

                    # 格式化时间
                    created_at_str = task.created_at.strftime("%Y-%m-%dT%H:%M:%S+ 08:00")

                    rows.append([
                        str(task.id),
                        str(task.user_id),
                        task.prompt or "",
                        review_msg,
                        created_at_str
                    ])

                print_info(f"🚨 找到 {stats['total_count']} 条违规记录")
                print_table(headers, rows)

            elif stats_type == "user":
                # 用户违规次数统计
                headers = ["ID", "Username", "Violations"]
                rows = []

                for user_stats in stats["user_violations"]:
                    rows.append([
                        str(user_stats["user_id"]),
                        user_stats["username"],
                        str(user_stats["violation_count"])
                    ])

                print_info(f"👥 找到 {stats['total_count']} 个有违规记录的用户")
                print_table(headers, rows)
            else:
                print_error(f"❌ 未知的统计类型: {stats_type}")

        except Exception as e:
            print_error(f"❌ 执行命令时出错: {e}")

    def do_system_stats(self, arg):
        """系统统计信息: system_stats"""
        try:
            stats = self.admin_service.get_system_stats()

            print("📊 系统统计信息")
            print("═" * 50)
            print(f"👥 总用户数: {stats['total_users']}")
            print(f"✅ 活跃用户: {stats['active_users']}")
            print(f"❌ 封禁用户: {stats['banned_users']}")
            print(f"🖼️  总生成任务: {stats['total_tasks']}")
            print(f"📅 今日生成任务: {stats['today_tasks']}")
            print("═" * 50)

        except Exception as e:
            print_error(f"❌ 执行命令时出错: {e}")

    def do_help(self, arg):
        """显示帮助信息: help [命令名]"""
        if arg:
            # 显示特定命令的帮助
            super().do_help(arg)
        else:
            # 显示所有命令的帮助
            print("""
可用命令:

用户管理:
  ban <用户ID>              - 封禁指定用户
  unban <用户ID>            - 解封指定用户
  user_list [--banned|--active] - 列出用户（可选参数）

统计查询:
  stats [--from 日期] [--to 日期] - 生成记录统计
  illegal_stats <task|user> [--from 日期] [--to 日期] - 违规统计
  system_stats              - 系统统计信息

系统命令:
  clear                     - 清屏
  help [命令]               - 显示帮助信息
  exit/quit                 - 退出系统

示例:
  ban 1                    - 封禁用户ID为1的用户
  user_list --banned       - 列出所有被封禁的用户
  stats --from 2025-12-01 --to 2025-12-10 - 统计指定时间段
  illegal_stats user       - 统计用户违规次数
            """)

    def parse_args(self, arg_line):
        """解析命令行参数"""
        args = {}
        parts = arg_line.split()
        i = 0
        while i < len(parts):
            if parts[i].startswith('--'):
                if i + 1 < len(parts) and not parts[i + 1].startswith('--'):
                    args[parts[i]] = parts[i + 1]
                    i += 2
                else:
                    args[parts[i]] = True
                    i += 1
            else:
                if 'type' not in args:  # 第一个非选项参数作为类型
                    args['type'] = parts[i]
                i += 1
        return args

    def default(self, line):
        """处理未知命令"""
        print_error(f"❌ 未知命令: {line}")
        print("输入 'help' 查看可用命令")


def main():
    """主函数"""
    try:
        # 清屏并显示欢迎信息
        os.system('cls' if os.name == 'nt' else 'clear')
        cli = AdminCLI()
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n\n感谢使用 PICTCTUREDECK 后台管理系统!")
    except Exception as e:
        print_error(f"系统错误: {e}")


if __name__ == "__main__":
    main()