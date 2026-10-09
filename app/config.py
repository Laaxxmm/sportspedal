import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def _load_secret_key():
    """Use SECRET_KEY from the environment, else a key persisted on the data volume.

    A fresh random key per process logs everyone out and invalidates every open
    form's CSRF token on each restart or redeploy. Persisting it to DATA_DIR
    (the Railway volume) keeps sessions and forms valid across restarts.
    """
    env_key = os.environ.get('SECRET_KEY')
    if env_key:
        return env_key
    key_path = os.path.join(DATA_DIR, '.secret_key')
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(key_path):
            with open(key_path) as fh:
                key = fh.read().strip()
            if key:
                return key
        key = os.urandom(32).hex()
        with open(key_path, 'w') as fh:
            fh.write(key)
        return key
    except OSError:
        return os.urandom(32).hex()


_default_key = _load_secret_key()


class Config:
    SECRET_KEY = _default_key
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(DATA_DIR, 'sportspedal.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'img')
    # Phone camera photos are often 4-10MB and backup ZIPs grow with the data.
    # Images are shrunk to a 400px WebP thumbnail on save, so size on disk is small.
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    # Token valid for the whole session, so a long sale entry is not rejected on submit.
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
