from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum, Boolean, ForeignKey, JSON, func, \
    text
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.exc import SQLAlchemyError
import config
from datetime import datetime, timedelta
import hashlib
import secrets
import os
from typing import Optional, List
from werkzeug.security import check_password_hash, generate_password_hash

# 创建基类 - SQLAlchemy 2.0 方式
Base = declarative_base()

# 确保数据目录存在
os.makedirs("data", exist_ok=True)

# 创建数据库引擎 - 使用文件数据库实现持久化
# engine = create_engine(
#     config.Config.DATABASE_URL.replace("sqlite:///",
#                                        "sqlite:///data/") if ":memory:" not in config.Config.DATABASE_URL else config.Config.DATABASE_URL,
#     echo=False,
#     connect_args={'check_same_thread': False}
# )
engine = create_engine(
    config.Config.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=config.Config.DB_POOL_SIZE,
    max_overflow=config.Config.DB_MAX_OVERFLOW,
    pool_recycle=config.Config.DB_POOL_RECYCLE,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """测试数据库连接"""
    try:
        with engine.connect() as conn:
            return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


# 密码安全工具函数
def hash_password(password: str) -> str:
    """对密码进行安全哈希处理"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # 迭代次数，增加破解难度
    ).hex()
    return f"{password_hash}:{salt}"


def verify_password(password: str, hashed_password: str) -> bool:
    """验证密码是否正确"""
    try:
        if not hashed_password or ':' not in hashed_password:
            return False
        password_hash, salt = hashed_password.split(':')
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return new_hash == password_hash
    except Exception:
        return False


# 会话管理表
class AdminSession(Base):
    __tablename__ = 'admin_sessions'

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(64), unique=True, index=True, nullable=False)
    admin_user_id = Column(Integer, nullable=False)
    username = Column(String(50), nullable=False)
    login_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_activity = Column(DateTime, nullable=False, default=datetime.utcnow)
    ip_address = Column(String(45))  # 支持IPv6
    user_agent = Column(String(255))
    is_active = Column(Boolean, nullable=False, default=True)

    def is_expired(self):
        """检查会话是否过期"""
        expiration_time = self.last_activity + timedelta(minutes=config.Config.SESSION_TIMEOUT_MINUTES)
        return datetime.utcnow() > expiration_time


class LoginAttempt(Base):
    __tablename__ = 'login_attempts'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    ip_address = Column(String(45), nullable=False)
    attempt_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    success = Column(Boolean, nullable=False)


# 定义数据模型
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum('user', 'admin', name='user_role'), nullable=False, default='user')
    status = Column(Enum('active', 'banned', name='user_status'), nullable=False, default='active')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    generations = relationship("Generation", back_populates="user")
    collections = relationship("Collection", back_populates="user")
    nfts = relationship("NFT", back_populates="owner")

    def to_dict(self):
        """转换为字典格式（排除敏感信息）"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class Generation(Base):
    __tablename__ = 'generations'

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(Enum('queued', 'processing', 'completed', 'failed', name='task_status'),
                    nullable=False, default='queued')
    generation_type = Column(Enum('t2i', 'i2i', 't2v', 'i2v', name='generation_type'), nullable=False)
    prompt = Column(Text)
    parameters = Column(JSON)
    result_url = Column(String(512))
    physical_path = Column(String(512))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # 关系
    user = relationship("User", back_populates="generations")
    collections = relationship("Collection", back_populates="generation")
    nft = relationship("NFT", back_populates="generation", uselist=False)


class Collection(Base):
    __tablename__ = 'collections'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('collections.id'))
    name = Column(String(100), nullable=False)
    node_type = Column(Enum('folder', 'file', name='node_type'), nullable=False)
    generation_id = Column(Integer, ForeignKey('generations.id'))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="collections")
    generation = relationship("Generation", back_populates="collections")
    parent = relationship("Collection", remote_side=[id], backref="children")


class NFT(Base):
    __tablename__ = 'nfts'

    id = Column(Integer, primary_key=True, index=True)
    generation_id = Column(Integer, ForeignKey('generations.id'), nullable=False)
    owner_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token_id = Column(String(255))
    contract_address = Column(String(255), nullable=False)
    transaction_hash = Column(String(255))
    status = Column(Enum('pending', 'confirmed', 'failed', name='nft_status'),
                    nullable=False, default='pending')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    confirmed_at = Column(DateTime)

    # 关系
    generation = relationship("Generation", back_populates="nft")
    owner = relationship("User", back_populates="nfts")


def init_db():
    """初始化数据库并创建测试数据"""
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建完成")

        db = SessionLocal()
        try:
            # 检查是否已有数据
            user_count = db.scalar(text("SELECT COUNT(*) FROM users"))

            if user_count == 0:
                print("开始创建测试数据...")

                # 创建默认管理员账户（密码：admin123）
                admin_password_hash = generate_password_hash("admin123")
                admin_user = User(
                    username="admin",
                    email="admin@pictcturdeck.com",
                    password_hash=admin_password_hash,
                    role="admin",
                    status="active"
                )
                db.add(admin_user)

                # 创建测试用户
                test_users = [
                    User(
                        username="test_user1",
                        email="user1@test.com",
                        password_hash=generate_password_hash("password1"),
                        role="user",
                        status="active"
                    ),
                    User(
                        username="test_user2",
                        email="user2@test.com",
                        password_hash=generate_password_hash("password2"),
                        role="user",
                        status="banned"
                    ),
                    User(
                        username="super_user",
                        email="super@test.com",
                        password_hash=generate_password_hash("super123"),
                        role="admin",
                        status="active"
                    ),
                    User(
                        username="violation_user",
                        email="violation@test.com",
                        password_hash=generate_password_hash("password3"),
                        role="user",
                        status="active"
                    )
                ]

                for user in test_users:
                    db.add(user)

                db.flush()

                # 创建测试生成记录
                test_generations = [
                    Generation(
                        uuid="550e8400-e29b-41d4-a716-446655440000",
                        user_id=2,  # test_user1
                        status="completed",
                        generation_type="t2i",
                        prompt="一只可爱的猫咪在草地上玩耍",
                        parameters='{"model": "stable-diffusion", "steps": 50}',
                        result_url="http://example.com/image1.png",
                        physical_path="/storage/images/t2i/2025/12/01/550e8400.png",
                        created_at=datetime(2025, 12, 1, 10, 30, 0),
                        completed_at=datetime(2025, 12, 1, 10, 31, 0)
                    ),
                    Generation(
                        uuid="550e8400-e29b-41d4-a716-446655440001",
                        user_id=2,
                        status="completed",
                        generation_type="t2v",
                        prompt="美丽的星空延时视频",
                        parameters='{"model": "video-diffusion", "duration": 5}',
                        result_url="http://example.com/video1.mp4",
                        physical_path="/storage/videos/t2v/2025/12/02/550e8401.mp4",
                        created_at=datetime(2025, 12, 2, 14, 20, 0),
                        completed_at=datetime(2025, 12, 2, 14, 25, 0)
                    ),
                    Generation(
                        uuid="550e8400-e29b-41d4-a716-446655440002",
                        user_id=3,  # test_user2 (banned)
                        status="failed",
                        generation_type="i2i",
                        prompt="包含不当内容的图片",
                        parameters='{"model": "stable-diffusion", "steps": 30}',
                        result_url=None,
                        physical_path=None,
                        created_at=datetime(2025, 12, 3, 9, 15, 0),
                        completed_at=datetime(2025, 12, 3, 9, 16, 0)
                    ),
                    Generation(
                        uuid="550e8400-e29b-41d4-a716-446655440003",
                        user_id=5,  # violation_user
                        status="completed",
                        generation_type="t2i",
                        prompt="暴力场景图片",
                        parameters='{"model": "stable-diffusion", "steps": 40}',
                        result_url="http://example.com/image2.png",
                        physical_path="/storage/images/t2i/2025/12/04/550e8403.png",
                        created_at=datetime(2025, 12, 4, 11, 20, 0),
                        completed_at=datetime(2025, 12, 4, 11, 21, 0)
                    ),
                    Generation(
                        uuid="550e8400-e29b-41d4-a716-446655440004",
                        user_id=5,
                        status="completed",
                        generation_type="t2i",
                        prompt="色情内容图片",
                        parameters='{"model": "stable-diffusion", "steps": 40}',
                        result_url="http://example.com/image3.png",
                        physical_path="/storage/images/t2i/2025/12/05/550e8404.png",
                        created_at=datetime(2025, 12, 5, 15, 30, 0),
                        completed_at=datetime(2025, 12, 5, 15, 31, 0)
                    )
                ]

                for generation in test_generations:
                    db.add(generation)

                db.commit()
                print("✅ 测试数据创建完成")
            else:
                print("✅ 数据库已存在，跳过测试数据创建")

        except Exception as e:
            print(f"❌ 初始化数据库时出错: {e}")
            db.rollback()
        finally:
            db.close()

    except Exception as e:
        print(f"❌ 创建数据库表时出错: {e}")


def cleanup_expired_sessions():
    """清理过期会话"""
    db = SessionLocal()
    try:
        expired_sessions = db.query(AdminSession).filter(
            AdminSession.last_activity < datetime.utcnow() - timedelta(minutes=config.Config.SESSION_TIMEOUT_MINUTES)
        ).all()

        for session in expired_sessions:
            session.is_active = False

        db.commit()
        cleaned_count = len(expired_sessions)
        if cleaned_count > 0:
            print(f"🧹 已清理 {cleaned_count} 个过期会话")
        return cleaned_count
    except Exception as e:
        print(f"❌ 清理过期会话时出错: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


# 认证服务类
class AuthService:
    """认证服务"""

    def __init__(self, db):
        self.db = db

    def authenticate_admin(self, username: str, password: str, ip_address: str = "127.0.0.1") -> dict:
        """管理员认证"""
        try:
            # 检查登录尝试次数
            recent_failed_attempts = self.db.query(LoginAttempt).filter(
                LoginAttempt.ip_address == ip_address,
                LoginAttempt.attempt_time >= datetime.utcnow() - timedelta(minutes=30),
                LoginAttempt.success == False
            ).count()

            if recent_failed_attempts >= config.Config.MAX_LOGIN_ATTEMPTS:
                raise ValueError("登录尝试次数过多，请30分钟后再试")

            # 查找用户
            user = self.db.query(User).filter(
                User.username == username,
                User.role == 'admin'
            ).first()

            # 验证密码
            is_success = user is not None and user.status == 'active' and check_password_hash(user.password_hash, password)

            # 记录登录尝试
            attempt = LoginAttempt(
                username=username,
                ip_address=ip_address,
                attempt_time=datetime.utcnow(),
                success=is_success
            )
            self.db.add(attempt)
            self.db.commit()

            if not is_success:
                raise ValueError("Incorrect username or password")

            # 创建会话
            session_token = secrets.token_hex(32)
            session = AdminSession(
                session_token=session_token,
                admin_user_id=user.id,
                username=user.username,
                login_time=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                ip_address=ip_address,
                is_active=True
            )

            self.db.add(session)
            self.db.commit()

            return {
                "session_token": session_token,
                "user_id": user.id,
                "username": user.username,
                "login_time": session.login_time
            }

        except SQLAlchemyError as e:
            self.db.rollback()
            raise ValueError(f"数据库错误: {e}")

    def validate_session(self, session_token: str) -> bool:
        """验证会话有效性"""
        if not session_token:
            return False

        session = self.db.query(AdminSession).filter(
            AdminSession.session_token == session_token,
            AdminSession.is_active == True
        ).first()

        if not session:
            return False

        if session.is_expired():
            session.is_active = False
            self.db.commit()
            return False

        # 更新最后活动时间
        session.last_activity = datetime.utcnow()
        self.db.commit()

        return True

    def get_session_user(self, session_token: str) -> Optional[dict]:
        """获取会话对应的用户信息"""
        if not self.validate_session(session_token):
            return None

        session = self.db.query(AdminSession).filter(
            AdminSession.session_token == session_token
        ).first()

        if not session:
            return None

        return {
            "user_id": session.admin_user_id,
            "username": session.username,
            "login_time": session.login_time
        }

    def logout(self, session_token: str) -> bool:
        """注销登录"""
        session = self.db.query(AdminSession).filter(
            AdminSession.session_token == session_token
        ).first()

        if session:
            session.is_active = False
            self.db.commit()
            return True

        return False

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """修改用户密码"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("用户不存在")

            if not check_password_hash(user.password_hash, old_password):
                raise ValueError("原密码错误")

            user.password_hash = generate_password_hash(new_password)
            user.updated_at = datetime.utcnow()
            self.db.commit()
            return True

        except SQLAlchemyError as e:
            self.db.rollback()
            raise ValueError(f"修改密码失败: {e}")


# 后台管理服务类
class AdminService:
    """后台管理服务"""

    def __init__(self, db):
        self.db = db
        self.auth_service = AuthService(db)

    def ban_user(self, user_id: int) -> bool:
        """封禁用户"""
        # 检查用户是否存在
        user = self.db.get(User, user_id)

        if not user:
            raise ValueError(f"User {user_id} does not exist.")

        if user.status == "banned":
            raise ValueError(f"User {user_id} has already been banned.")

        # 更新用户状态
        user.status = "banned"
        user.updated_at = datetime.now()
        self.db.commit()
        return True

    def unban_user(self, user_id: int) -> bool:
        """解封用户"""
        # 检查用户是否存在
        user = self.db.get(User, user_id)

        if not user:
            raise ValueError(f"User {user_id} does not exist.")

        if user.status == "active":
            raise ValueError(f"User {user_id} is not banned.")

        # 更新用户状态
        user.status = "active"
        user.updated_at = datetime.now()
        self.db.commit()
        return True

    def get_users(self, banned_only: bool = False, active_only: bool = False) -> List[User]:
        """获取用户列表"""
        query = self.db.query(User).filter(User.role == "user")

        if banned_only:
            query = query.filter(User.status == "banned")
        elif active_only:
            query = query.filter(User.status == "active")

        return query.all()

    def get_generation_stats(
            self,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
    ) -> List[Generation]:
        """获取生成记录统计"""
        query = self.db.query(Generation)

        if start_date and end_date:
            if start_date > end_date:
                raise ValueError("Start date is after end date.")

            query = query.filter(
                Generation.created_at.between(start_date, end_date)
            )
        elif start_date or end_date:
            raise ValueError("错误: 必须同时提供开始日期和结束日期")

        query = query.order_by(Generation.created_at.desc())
        return query.all()

    def get_illegal_stats(
            self,
            stats_type: str,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
    ) -> dict:
        """获取违规统计"""
        if stats_type == "task":
            # 违规任务统计
            query = self.db.query(Generation).filter(
                Generation.status == "completed"
            )

            if start_date and end_date:
                query = query.filter(
                    Generation.created_at.between(start_date, end_date)
                )

            tasks = query.order_by(Generation.created_at.desc()).all()

            # 模拟违规检测
            violation_tasks = []
            for task in tasks:
                if task.prompt and any(keyword in task.prompt.lower() for keyword in ["暴力", "色情", "违法", "暴露"]):
                    violation_tasks.append(task)

            return {
                "type": "task",
                "violation_tasks": violation_tasks,
                "total_count": len(violation_tasks)
            }

        elif stats_type == "user":
            # 用户违规次数统计
            users = self.get_users()
            user_violations = []

            for user in users:
                # 查询该用户的生成任务
                user_tasks = self.db.query(Generation).filter(Generation.user_id == user.id).all()

                # 统计违规任务数量
                violation_count = 0
                for task in user_tasks:
                    if task.prompt and any(keyword in task.prompt.lower() for keyword in ["暴力", "色情", "违法", "暴露"]):
                        violation_count += 1

                if violation_count > 0:
                    user_violations.append({
                        "user_id": user.id,
                        "username": user.username,
                        "violation_count": violation_count
                    })

            # 按违规次数降序排序
            user_violations.sort(key=lambda x: x["violation_count"], reverse=True)

            return {
                "type": "user",
                "user_violations": user_violations,
                "total_count": len(user_violations)
            }

        else:
            raise ValueError("错误: 统计类型必须是 'task' 或 'user'")

    def get_system_stats(self) -> dict:
        """获取系统统计信息"""
        # 总用户数
        total_users = self.db.query(User).filter(User.role == "user").count()

        # 活跃用户数
        active_users = self.db.query(User).filter(
            User.role == "user",
            User.status == "active"
        ).count()

        # 封禁用户数
        banned_users = self.db.query(User).filter(
            User.role == "user",
            User.status == "banned"
        ).count()

        # 总生成任务数
        total_tasks = self.db.query(Generation).count()

        # 今日生成任务数
        today = datetime.now().date()
        today_tasks = self.db.query(Generation).filter(
            func.date(Generation.created_at) == today
        ).count()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "banned_users": banned_users,
            "total_tasks": total_tasks,
            "today_tasks": today_tasks
        }

    def login(self, username: str, password: str, ip_address: str = "127.0.0.1") -> dict:
        """管理员登录"""
        return self.auth_service.authenticate_admin(username, password, ip_address)

    def validate_session(self, session_token: str) -> bool:
        """验证会话有效性"""
        return self.auth_service.validate_session(session_token)

    def get_session_user(self, session_token: str) -> Optional[dict]:
        """获取会话用户信息"""
        return self.auth_service.get_session_user(session_token)

    def logout(self, session_token: str) -> bool:
        """注销登录"""
        return self.auth_service.logout(session_token)

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """修改密码"""
        return self.auth_service.change_password(user_id, old_password, new_password)

if __name__ == "__main__":
    # 初始化数据库
    init_db()
    test_connection()

    # 清理过期会话
    cleanup_expired_sessions()