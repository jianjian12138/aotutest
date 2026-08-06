from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from decouple import config as decouple_config
from backend.utils.config import get_config
import os

BASE_DIR = Path(__file__).resolve().parent.parent

_INSECURE_DEFAULT_KEYS = {
    '', 'django-insecure-your-secret-key-here', 'django-insecure-change-me-in-production',
}


def _env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in ('1', 'true', 'yes', 'on')


# ---- 配置优先级：环境变量 > config.yaml > 安全默认值 ----
# DEBUG 默认 False（安全默认），仅在显式开启时为 True
DEBUG = _env_bool('DEBUG', bool(get_config('server.debug', False)))

SECRET_KEY = os.environ.get('SECRET_KEY') or get_config('server.secret_key', '')
if SECRET_KEY in _INSECURE_DEFAULT_KEYS:
    if DEBUG:
        # 开发环境兜底：允许运行但给出显著警告
        SECRET_KEY = 'django-insecure-dev-only-do-not-use-in-production'
        import warnings
        warnings.warn('SECRET_KEY 未配置，正在使用开发用不安全密钥。生产环境必须设置环境变量 SECRET_KEY！')
    else:
        raise ImproperlyConfigured(
            '生产环境（DEBUG=False）必须通过环境变量 SECRET_KEY 提供强密钥，拒绝使用默认弱密钥启动。'
        )

# ALLOWED_HOSTS：生产必须显式白名单
if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [
        s.strip() for s in os.environ.get(
            'ALLOWED_HOSTS',
            decouple_config('ALLOWED_HOSTS', default='localhost,127.0.0.1')
        ).split(',') if s.strip()
    ]

DJANGO_APPS = [
    'simpleui',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',  # 添加JWT支持
    'rest_framework_simplejwt.token_blacklist',  # JWT token黑名单
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'django_q',  # Django-Q2 Task Queue
]

LOCAL_APPS = [
    'apps.core_platform',

    # 路线三 · Phase 0 权限制高点：租户功能开关（agent 测评 / LLM 测试 等能力按租户开通）
    'apps.tenant_features',

    # 路线三 · Phase 2 核心：eval-native 评测舱（数据集 / 评估引擎 / 严格租户隔离）
    'apps.eval_pod',

    'apps.testcases',
    'apps.testsuites',
    'apps.executions',
    'apps.reports',
    'apps.reviews',

    'apps.assistant',
    'apps.requirement_analysis',
    'apps.api_testing',
    'apps.ui_automation.apps.UiAutomationConfig',
    'apps.data_factory',
    'apps.performance_test',
    'apps.knowledge_graph',
    'apps.scheduler',

    'apps.special_testing',
    'apps.cicd',
    'apps.strix_security',
    'apps.notifications',
    'apps.defects',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'backend.middleware.StandardResponseMiddleware',  # V2 Global Wrapper Layer
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'backend.middleware.AuditLogMiddleware',  # 阶段1.3 操作审计留痕
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

# 数据库：环境变量（容器/生产） > config.yaml（本地开发） > SQLite 默认
db_engine = os.environ.get('DB_ENGINE') or get_config('database.engine', 'django.db.backends.sqlite3')
db_name = os.environ.get('DB_NAME') or get_config('database.name', 'db.sqlite3')

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        'NAME': BASE_DIR / db_name if db_engine == 'django.db.backends.sqlite3' else db_name,
        'USER': os.environ.get('DB_USER') or get_config('database.user', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD') or get_config('database.password', ''),
        'HOST': os.environ.get('DB_HOST') or get_config('database.host', ''),
        'PORT': os.environ.get('DB_PORT') or get_config('database.port', ''),
    }
}

if not DEBUG and db_engine == 'django.db.backends.sqlite3':
    import warnings
    warnings.warn('生产环境（DEBUG=False）正在使用 SQLite，存在并发写入瓶颈，强烈建议切换 PostgreSQL/MySQL。')

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True  # 移除重复定义

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'core_platform.User'

# DRF Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT认证（优先）
        'rest_framework.authentication.TokenAuthentication',  # 保留Token认证（兼容）
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# JWT Settings
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),  # access_token 60分钟
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),  # refresh_token 7天
    'ROTATE_REFRESH_TOKENS': True,  # 刷新时轮换refresh_token
    'BLACKLIST_AFTER_ROTATION': True,  # 旧的refresh_token加入黑名单
    'UPDATE_LAST_LOGIN': True,  # 更新最后登录时间

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),

    # httpOnly JWT Cookie 鉴权（前端不再依赖 localStorage）
    'AUTH_COOKIE': 'access_token',
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_SECURE': not DEBUG,
    'AUTH_COOKIE_SAMESITE': 'Strict',
    'REFRESH_TOKEN_COOKIE': 'refresh_token',
    'REFRESH_TOKEN_COOKIE_HTTP_ONLY': True,
    'REFRESH_TOKEN_COOKIE_SECURE': not DEBUG,
    'REFRESH_TOKEN_COOKIE_SAMESITE': 'Strict',
}

# CSRF Settings - 根据DEBUG模式设置
if DEBUG:
    CSRF_COOKIE_SECURE = False
    CSRF_USE_SESSIONS = False
    CSRF_COOKIE_HTTPONLY = False
    CSRF_COOKIE_SAMESITE = 'Lax'
else:
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = 'Strict'

# CORS Settings
if DEBUG:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5656",
        "http://127.0.0.1:5656",
        "http://localhost:5566",
        "http://127.0.0.1:5566",
    ]
    CORS_ALLOW_CREDENTIALS = True
else:
    CORS_ALLOWED_ORIGINS = [
        s.strip() for s in os.environ.get(
            'CORS_ALLOWED_ORIGINS',
            decouple_config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000')
        ).split(',') if s.strip()
    ]
    CORS_ALLOW_CREDENTIALS = True

# CSRF Settings
if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4545",
        "http://127.0.0.1:4545",
        "http://localhost:5566",
        "http://127.0.0.1:5566",
    ]
else:
    CSRF_TRUSTED_ORIGINS = [
        s.strip() for s in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if s.strip()
    ] or CORS_ALLOWED_ORIGINS

# 生产安全加固
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', not DEBUG)  # 有 HTTPS 时置 True
    SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', not DEBUG)

# Spectacular Settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Testing API',
    'DESCRIPTION': 'Test Case Management Platform API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ==========================================
# Task Queue Settings (Django-Q2)
# ==========================================
Q_CLUSTER = {
    'name': 'TestHub_Q_Cluster',
    'workers': 4,
    'recycle': 500,
    'timeout': 1800,  # 30 minutes to match previous CELERY_TASK_TIME_LIMIT
    'retry': 1860,    # Must be larger than timeout
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'orm': 'default',  # Default to Django ORM to simplify deployment
}

# 邮件配置（可选）
EMAIL_BACKEND = 'apps.api_testing.custom_email_backend.CustomEmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.163.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 465))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)



# 确保日志目录存在
log_dir = os.path.join(BASE_DIR, 'logs')
os.makedirs(log_dir, exist_ok=True)

# Logging Configuration with Rotation
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,  # 保留5个备份
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps.api_testing.views': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'apps.api_testing.serializers': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# 指定simpleui默认的主题,指定一个文件名，相对路径就从simpleui的theme目录读取
SIMPLEUI_DEFAULT_THEME = 'admin.lte.css'
# 是否显示图标
SIMPLEUI_DEFAULT_ICON = True
# 是否关闭登录页粒子效果
SIMPLEUI_LOGIN_PARTICLES = True
# 后台管理首页，可以是url或者html文件
# SIMPLEUI_HOME_PAGE = 'https://www.baidu.com/'  # 后面可以扩展为大屏显示做统计
# 自定义首页标题
# SIMPLEUI_HOME_TITLE = 'Dashboard'
# # 自定义首页图标 首页图标,支持element-ui和fontawesome的图标，参考https://fontawesome.com/icons图标
# SIMPLEUI_HOME_ICON = 'fa fa-gauge'
# 设置simpleui 点击首页图标跳转的地址
SIMPLEUI_INDEX = 'http://localhost:4545'
# 自定义后台的Logo
SIMPLEUI_LOGO = 'https://static.djangoproject.com/img/favicon.6dbf28c0650e.ico'
# 是否显示首页信息
SIMPLEUI_HOME_INFO = False
# 是否显示快捷入口
SIMPLEUI_HOME_QUICK = True
# 是否显示最近动作
SIMPLEUI_HOME_ACTION = True
# 使用分析
SIMPLEUI_ANALYSIS = False
# 离线模式
SIMPLEUI_STATIC_OFFLINE = True
# True或None 默认显示加载遮罩层，指定为False 不显示遮罩层。默认显示
SIMPLEUI_LOADING = True
# 设置菜单icon，参考https://element.eleme.cn/#/zh-CN/component/icon
SIMPLEUI_ICON = {
    # 一级菜单项
    '测试执行管理': 'el-icon-s-tools',
    '用户管理': 'el-icon-user-solid',
    '令牌黑名单': 'el-icon-warning-outline',
    '接口测试': 'el-icon-s-platform',
    '智能助手': 'el-icon-chat-dot-round',
    '用例评审管理': 'el-icon-edit-outline',
    '认证令牌': 'el-icon-key',
    '认证和授权': 'el-icon-s-check',
    '需求分析': 'el-icon-notebook-2',

    # 二级菜单项
    '测试执行': 'el-icon-s-operation',
    '测试执行历史': 'el-icon-time',
    '测试执行用例': 'el-icon-document',
    '测试计划': 'el-icon-document-checked',
    '用户': 'el-icon-user',
    '用户配置': 'el-icon-setting',
    'Blacklisted Tokens': 'el-icon-warning-outline',
    'Outstanding Tokens': 'el-icon-s-custom',
    'API请求': 'el-icon-s-promotion',
    'API集合': 'el-icon-s-grid',
    'API项目': 'el-icon-s-custom',
    '任务执行日志': 'el-icon-s-data',
    '定时任务': 'el-icon-time',
    '测试套件': 'el-icon-suitcase',
    '环境变量': 'el-icon-school',
    '请求历史': 'el-icon-odometer',
    '智能助手会话': 'el-icon-chat-dot-round',
    '智能助手消息': 'el-icon-message',
    '测试用例评审': 'el-icon-check',
    '评审分配': 'el-icon-guide',
    '评审意见': 'el-icon-s-custom',
    '评审模板': 'el-icon-document',
    'Tokens': 'el-icon-key',
    '组': 'el-icon-s-custom',
    '业务需求': 'el-icon-document-checked',
    '分析任务': 'el-icon-stopwatch',
    '生成的测试用例': 'el-icon-document',
    '需求文档': 'el-icon-document',
}
