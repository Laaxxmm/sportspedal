import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sportspedal-dev-key-change-in-prod')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(DATA_DIR, 'sportspedal.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'img')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB max upload
