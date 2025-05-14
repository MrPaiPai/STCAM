import os
from pathlib import Path



# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
print("BASE_DIR:", BASE_DIR)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# Security settings
SECRET_KEY = 'thepai2547007'  # ควรเป็นคีย์ที่ปลอดภัยใน production
DEBUG = True
ALLOWED_HOSTS = ['stcam.onrender.com', 'localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'myapp',
    'crispy_forms',
    'crispy_bootstrap5',
    'widget_tweaks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'myapp.middleware.SessionTimeoutMiddleware',  # เหลือแค่อันนี้อันเดียว
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # เพิ่มโฟลเดอร์ templates
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

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'th'
TIME_ZONE = 'Asia/Bangkok'

# USE_I18N = True
USE_I18N = False

USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

print("STATIC_ROOT:", STATIC_ROOT)


# Media files (สำหรับการอัปโหลดไฟล์สื่อ)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
print("MEDIA_ROOT:", MEDIA_ROOT)

# Storage settings (สำหรับ Django 5.1.3)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

DEBUG = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'myapp.CustomUser'

# Crispy Forms settings
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Logout redirect
LOGOUT_REDIRECT_URL = '/'

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Session settings
SESSION_COOKIE_AGE = 1800  # 30 นาที (คิดเป็นวินาที)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Session จะหมดอายุเมื่อปิดเบราว์เซอร์
SESSION_SAVE_EVERY_REQUEST = True  # บันทึก session ทุกครั้งที่มีการเรียกใช้
SESSION_EXPIRE_SECONDS = 1800  # กำหนด session timeout เป็น 30 นาที (1800 วินาที)
SESSION_EXPIRE_AFTER_LAST_ACTIVITY = True  # Reset session timeout ทุกครั้งที่มีการใช้งาน
SESSION_TIMEOUT_REDIRECT = 'session_expired'  # ชื่อ url ที่จะ redirect ไป

LOGIN_REDIRECT_URL = '/'  

# กำหนดเส้นทางสำหรับเก็บไฟล์แปลภาษา
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]