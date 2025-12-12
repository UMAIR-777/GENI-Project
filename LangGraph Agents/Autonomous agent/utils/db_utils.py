from sqlalchemy     import create_engine
from utils.config   import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT


def get_engine(database: str):
    url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{database}"
    return create_engine(url)