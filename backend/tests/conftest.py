import os

# Tests build SQL without connecting, so any MySQL URL is enough.
os.environ.setdefault("DATABASE_URL", "mysql+pymysql://test:test@127.0.0.1:3306/test")
