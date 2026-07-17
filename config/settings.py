import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    # Local apps
    'core',
    'users.apps.UsersConfig',
    'candidates',
    'votes',
    'gifts',
    'payments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.FrontendRequestLogMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'voting_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Aliyun OSS
OSS_ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', '')
OSS_ACCESS_KEY_SECRET = os.getenv('OSS_ACCESS_KEY_SECRET', '')
ALIYUN_OSS_BUCKET = os.getenv('ALIYUN_OSS_BUCKET', os.getenv('OSS_BUCKET', ''))
OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', 'oss-cn-hangzhou.aliyuncs.com')
OSS_BASE_URL = os.getenv('OSS_BASE_URL', '')
OSS_STS_ROLE_ARN = os.getenv('OSS_STS_ROLE_ARN', '')
OSS_REGION = os.getenv('OSS_REGION', os.getenv('ALIYUN_SMS_REGION', 'cn-hangzhou'))
OSS_STS_DURATION_SECONDS = int(os.getenv('OSS_STS_DURATION_SECONDS', '3600'))

_USE_OSS = bool(OSS_ACCESS_KEY_ID and OSS_ACCESS_KEY_SECRET and ALIYUN_OSS_BUCKET)
if _USE_OSS:
  STORAGES = {
    'default': {
      'BACKEND': 'core.storage.AliyunOSSStorage',
    },
    'staticfiles': {
      'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
  }
  MEDIA_URL = os.getenv('MEDIA_URL', f'https://{ALIYUN_OSS_BUCKET}.{OSS_ENDPOINT}/')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin.strip()
]

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
}

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', '60'))
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME_DAYS', '7'))
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# drf-spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': '海选投票 API',
    'DESCRIPTION': '海选投票系统后端接口文档，包含用户登录、投票、礼物、支付等功能。',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/',
    'TAGS': [
        {'name': '认证', 'description': '手机号登录与 JWT 鉴权'},
        {'name': '候选人', 'description': '候选人信息与排行榜'},
        {'name': '报名', 'description': '用户自主报名与审核进度查询'},
        {'name': '投票', 'description': '投票相关接口'},
        {'name': '礼物', 'description': '礼物购买与赠送'},
        {'name': '支付', 'description': '微信支付与支付宝支付'},
        {'name': '配置', 'description': '系统配置'},
    ],
}

# SMS
SMS_DEV_MODE = os.getenv('SMS_DEV_MODE', 'True').lower() == 'true'
SMS_DEV_CODE = os.getenv('SMS_DEV_CODE', '123456')
ALIYUN_SMS_ACCESS_KEY_ID = os.getenv('ALIYUN_SMS_ACCESS_KEY_ID', '')
ALIYUN_SMS_ACCESS_KEY_SECRET = os.getenv('ALIYUN_SMS_ACCESS_KEY_SECRET', '')
ALIYUN_SMS_REGION = os.getenv('ALIYUN_SMS_REGION', 'cn-hangzhou')
ALIYUN_SMS_SIGN_NAME = os.getenv('ALIYUN_SMS_SIGN_NAME', '')
ALIYUN_SMS_TEMPLATE_CODE = os.getenv('ALIYUN_SMS_TEMPLATE_CODE', '')

# WeChat Pay APIv3（Native 扫码 + 商家转账提现）
# 兼容旧变量名 WECHAT_APP_ID / WECHAT_MCH_ID / WECHAT_NOTIFY_URL
WECHAT_PAY_APP_ID = os.getenv('WECHAT_PAY_APP_ID', os.getenv('WECHAT_APP_ID', ''))
WECHAT_PAY_MCH_ID = os.getenv('WECHAT_PAY_MCH_ID', os.getenv('WECHAT_MCH_ID', ''))
WECHAT_PAY_MCH_SERIAL_NO = os.getenv('WECHAT_PAY_MCH_SERIAL_NO', '')
WECHAT_PAY_MCH_PRIVATE_KEY = os.getenv('WECHAT_PAY_MCH_PRIVATE_KEY', '')
WECHAT_PAY_API_V3_KEY = os.getenv('WECHAT_PAY_API_V3_KEY', os.getenv('WECHAT_API_KEY', ''))
WECHAT_PAY_PLATFORM_PUBLIC_KEY_PEM = os.getenv('WECHAT_PAY_PLATFORM_PUBLIC_KEY_PEM', '')
# 微信支付公钥 ID（形如 PUB_KEY_ID_xxx），不是 pem 文件路径；商家转账必填
WECHAT_PAY_PLATFORM_SERIAL_NO = os.getenv('WECHAT_PAY_PLATFORM_SERIAL_NO', '')
WECHAT_PAY_NOTIFY_URL = os.getenv(
  'WECHAT_PAY_NOTIFY_URL',
  os.getenv('WECHAT_NOTIFY_URL', ''),
)
WECHAT_PAY_WITHDRAW_NOTIFY_URL = os.getenv('WECHAT_PAY_WITHDRAW_NOTIFY_URL', '')
WECHAT_PAY_TRANSFER_SCENE_ID = os.getenv('WECHAT_PAY_TRANSFER_SCENE_ID', '1005')

# 旧名兼容（部分历史代码）
WECHAT_APP_ID = WECHAT_PAY_APP_ID
WECHAT_MCH_ID = WECHAT_PAY_MCH_ID
WECHAT_API_KEY = WECHAT_PAY_API_V3_KEY
WECHAT_NOTIFY_URL = WECHAT_PAY_NOTIFY_URL

# Alipay（公钥证书模式，支持扫码支付 + 转账提现）
ALIPAY_APP_ID = os.getenv('ALIPAY_APP_ID', '')
ALIPAY_GATEWAY = os.getenv('ALIPAY_GATEWAY', 'https://openapi.alipay.com/gateway.do')
ALIPAY_APP_PRIVATE_KEY = os.getenv(
  'ALIPAY_APP_PRIVATE_KEY',
  os.getenv('ALIPAY_PRIVATE_KEY_PATH', ''),
)
ALIPAY_PUBLIC_KEY = os.getenv(
  'ALIPAY_PUBLIC_KEY',
  os.getenv('ALIPAY_PUBLIC_KEY_PATH', ''),
)
ALIPAY_APP_CERT = os.getenv('ALIPAY_APP_CERT', '')
ALIPAY_ROOT_CERT = os.getenv('ALIPAY_ROOT_CERT', '')
ALIPAY_NOTIFY_URL = os.getenv('ALIPAY_NOTIFY_URL', '')
ALIPAY_WITHDRAW_NOTIFY_URL = os.getenv('ALIPAY_WITHDRAW_NOTIFY_URL', '')
ALIPAY_RETURN_URL = os.getenv('ALIPAY_RETURN_URL', '')
ALIPAY_PRIVATE_KEY_PATH = ALIPAY_APP_PRIVATE_KEY
ALIPAY_PUBLIC_KEY_PATH = ALIPAY_PUBLIC_KEY

# 网关模块直接读 os.environ，这里把 settings 回填，保证一致性
for _k, _v in {
  'WECHAT_PAY_APP_ID': WECHAT_PAY_APP_ID,
  'WECHAT_PAY_MCH_ID': WECHAT_PAY_MCH_ID,
  'WECHAT_PAY_MCH_SERIAL_NO': WECHAT_PAY_MCH_SERIAL_NO,
  'WECHAT_PAY_MCH_PRIVATE_KEY': WECHAT_PAY_MCH_PRIVATE_KEY,
  'WECHAT_PAY_API_V3_KEY': WECHAT_PAY_API_V3_KEY,
  'WECHAT_PAY_PLATFORM_PUBLIC_KEY_PEM': WECHAT_PAY_PLATFORM_PUBLIC_KEY_PEM,
  'WECHAT_PAY_PLATFORM_SERIAL_NO': WECHAT_PAY_PLATFORM_SERIAL_NO,
  'WECHAT_PAY_NOTIFY_URL': WECHAT_PAY_NOTIFY_URL,
  'WECHAT_PAY_WALLET_NOTIFY_URL': WECHAT_PAY_WITHDRAW_NOTIFY_URL,
  'WECHAT_PAY_TRANSFER_SCENE_ID': WECHAT_PAY_TRANSFER_SCENE_ID,
  'ALIPAY_APP_ID': ALIPAY_APP_ID,
  'ALIPAY_GATEWAY': ALIPAY_GATEWAY,
  'ALIPAY_APP_PRIVATE_KEY': ALIPAY_APP_PRIVATE_KEY,
  'ALIPAY_PUBLIC_KEY': ALIPAY_PUBLIC_KEY,
  'ALIPAY_APP_CERT': ALIPAY_APP_CERT,
  'ALIPAY_ROOT_CERT': ALIPAY_ROOT_CERT,
}.items():
  if _v and not os.environ.get(_k):
    os.environ[_k] = str(_v)
