import os
from datetime import datetime


class Config:
    """
    PICTCTUREDECK 系统配置文件
    使用Python类形式管理配置，便于类型检查和代码提示
    """

    # ========== 数据库配置 ==========
    # 使用SQLite内存数据库（避免MySQL连接问题）
    DATABASE_URL = "mysql+pymysql://root:123456@localhost/aigc"

    # 数据库连接池配置
    DB_POOL_SIZE = 5
    DB_MAX_OVERFLOW = 10
    DB_POOL_RECYCLE = 3600

    # ========== 管理员配置 ==========
    ADMIN_USERNAMES = ["admin", "superuser"]
    DEFAULT_ADMIN_PASSWORD = "admin123"  # 首次使用后请修改

    # ========== 会话和认证配置 ==========
    SESSION_TIMEOUT_MINUTES = 120  # 会话超时时间（分钟）
    MAX_LOGIN_ATTEMPTS = 5  # 最大登录尝试次数
    PASSWORD_HASH_ALGORITHM = "sha256"

    # ========== 日期时间配置 ==========
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    TIME_FORMAT = "%H:%M:%S"

    # ========== 业务状态映射 ==========
    STATUS_MAP = {
        'active': '活跃',
        'banned': '已封禁',
        'queued': '排队中',
        'processing': '处理中',
        'completed': '已完成',
        'failed': '失败',
        'pending': '等待中',
        'confirmed': '已确认'
    }

    # ========== 生成类型映射 ==========
    GENERATION_TYPE_MAP = {
        't2i': '文生图',
        'i2i': '图生图',
        't2v': '文生视频',
        'i2v': '图生视频'
    }

    # ========== 文件存储配置 ==========
    # 基础路径配置
    IMAGE_BASE_PATH = "images"
    VIDEO_BASE_PATH = "videos"
    THUMBNAIL_BASE_PATH = "thumbnails"
    TEMP_BASE_PATH = "temp"

    # 文件大小限制（字节）
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB

    # 允许的文件扩展名
    ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv']

    # ========== 系统日志配置 ==========
    LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE = "pictcturdeck.log"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # ========== API和网络配置 ==========
    API_TIMEOUT = 30  # 秒
    MAX_CONCURRENT_TASKS = 10
    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 8000

    # ========== 审核和安全性配置 ==========
    # 内容审核关键词
    CONTENT_FILTER_KEYWORDS = [
        "暴力", "色情", "违法", "暴露", "不当", "敏感"
    ]

    # 自动审核开关
    AUTO_MODERATION_ENABLED = True
    MODERATION_THRESHOLD = 0.8  # 审核置信度阈值

    # ========== 性能和缓存配置 ==========
    CACHE_ENABLED = True
    CACHE_TTL = 300  # 缓存存活时间（秒）
    MAX_CACHE_SIZE = 1000

    # ========== 功能开关配置 ==========
    # 模块功能开关
    USER_REGISTRATION_ENABLED = True
    EMAIL_VERIFICATION_ENABLED = False
    CONTENT_MODERATION_ENABLED = True
    AUTO_CLEANUP_ENABLED = True

    # ========== 外部服务配置 ==========
    # SMTP邮件配置
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USE_TLS = True
    SMTP_USERNAME = ""
    SMTP_PASSWORD = ""

    # 对象存储配置
    OSS_ENDPOINT = ""
    OSS_ACCESS_KEY = ""
    OSS_SECRET_KEY = ""
    OSS_BUCKET_NAME = ""

    @classmethod
    def get_database_config(cls):
        """获取数据库配置字典"""
        return {
            'url': cls.DATABASE_URL,
            'pool_size': cls.DB_POOL_SIZE,
            'max_overflow': cls.DB_MAX_OVERFLOW,
            'pool_recycle': cls.DB_POOL_RECYCLE
        }

    @classmethod
    def get_storage_paths(cls):
        """获取存储路径配置"""
        return {
            'images': cls.IMAGE_BASE_PATH,
            'videos': cls.VIDEO_BASE_PATH,
            'thumbnails': cls.THUMBNAIL_BASE_PATH,
            'temp': cls.TEMP_BASE_PATH
        }

    @classmethod
    def validate_config(cls):
        """验证配置有效性"""
        errors = []

        # 检查必要的路径配置
        required_paths = [cls.IMAGE_BASE_PATH, cls.VIDEO_BASE_PATH,
                          cls.THUMBNAIL_BASE_PATH, cls.TEMP_BASE_PATH]
        for path in required_paths:
            if not path or not isinstance(path, str):
                errors.append(f"存储路径配置无效: {path}")

        # 检查数值配置范围
        if cls.MAX_LOGIN_ATTEMPTS <= 0:
            errors.append("最大登录尝试次数必须大于0")

        if cls.SESSION_TIMEOUT_MINUTES <= 0:
            errors.append("会话超时时间必须大于0")

        if cls.MAX_IMAGE_SIZE <= 0:
            errors.append("图片大小限制必须大于0")

        if cls.MAX_VIDEO_SIZE <= 0:
            errors.append("视频大小限制必须大于0")

        if errors:
            raise ValueError("配置验证失败: " + "; ".join(errors))

        return True

    @classmethod
    def to_dict(cls):
        """将配置转换为字典（敏感信息已过滤）"""
        config_dict = {}
        for key in dir(cls):
            if not key.startswith('_') and key.isupper():
                value = getattr(cls, key)
                # 过滤敏感信息
                if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key']):
                    config_dict[key] = '***HIDDEN***'
                else:
                    config_dict[key] = value
        return config_dict


# 开发环境配置
class DevelopmentConfig(Config):
    """开发环境配置"""
    LOG_LEVEL = "DEBUG"
    DATABASE_URL = "sqlite:///./data/dev.db"
    CACHE_ENABLED = False


# 测试环境配置
class TestingConfig(Config):
    """测试环境配置"""
    LOG_LEVEL = "DEBUG"
    DATABASE_URL = "sqlite:///:memory:"
    AUTO_MODERATION_ENABLED = False
    EMAIL_VERIFICATION_ENABLED = False


# 生产环境配置
class ProductionConfig(Config):
    """生产环境配置"""
    LOG_LEVEL = "WARNING"
    DATABASE_URL = "sqlite:///./data/prod.db"
    CACHE_ENABLED = True
    AUTO_CLEANUP_ENABLED = True


# 根据环境变量选择配置
def get_config():
    """根据环境变量获取对应的配置类"""
    env = os.getenv('PICTCTUREDECK_ENV', 'development').lower()

    config_map = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig
    }

    return config_map.get(env, Config)


# 当前使用的配置
CurrentConfig = get_config()

if __name__ == "__main__":
    # 配置验证测试
    try:
        CurrentConfig.validate_config()
        print("✅ 配置文件验证通过")
        print("📊 当前配置摘要:")
        config_summary = CurrentConfig.to_dict()
        for key, value in list(config_summary.items())[:10]:  # 只显示前10项
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")