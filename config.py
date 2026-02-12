import os
import sys
from dotenv import load_dotenv


load_dotenv()

USE_MYSQL = True

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

MYSQL_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 4000)),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "charset": "utf8mb4",
    "ssl_ca": resource_path(os.getenv("DB_SSL_CA", "isrgrootx1.pem")),
    "autocommit": True,
}

USE_ENCRYPTION = True
ENCRYPTION_CONFIG = {
    'password': os.getenv("ENCRYPTION_PASSWORD", "default_secret"),
    'salt': os.getenv("ENCRYPTION_SALT", "default_salt").encode(),
    'iterations': 100000
}