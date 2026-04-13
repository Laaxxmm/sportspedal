import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Generate a stable key from hostname if no env var set (better than hardcoded)
_default_key = os.environ.get('SECRET_KEY') or os.urandom(32).hex()


class Config:
    SECRET_KEY = _default_key
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(DATA_DIR, 'sportspedal.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'img')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB max upload
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour CSRF token validity
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
