import os
import platform
import psycopg2
from dotenv import load_dotenv

load_dotenv()
def get_connection():
    """
    Returns a new PostgreSQL connection.
    - On Windows or when DB_HOST is specified, uses a TCP connection
    - Else, uses a Unix socket for Cloud SQL
    """
    database_name = os.getenv("DB_NAME")
    database_user = os.getenv("DB_USER")
    database_password = os.getenv("DB_PASSWORD")
    cloud_sql_connection_name = os.getenv("CLOUD_SQL_CONNECTION_NAME")
    
    if not all([database_name, database_user, database_password]):
        raise ValueError("Missing required database environment variables.")

    # Check if we should use TCP connection (Windows or explicit host)
    if os.name == "nt" or platform.system() == "Windows" or os.getenv("DB_HOST"):
        return psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
    else:
        if not cloud_sql_connection_name:
            raise ValueError("CLOUD_SQL_CONNECTION_NAME is required for Unix socket connection")
            
        # Proper Unix socket path for Cloud SQL
        socket_path = f"/cloudsql/{cloud_sql_connection_name}"
        
        return psycopg2.connect(
            dbname=database_name,
            user=database_user,
            password=database_password,
            host=os.getenv("DB_HOST")
        )


# import os
# import psycopg2

# def get_connection():
#     return psycopg2.connect(
#         database_name = os.getenv("DATABASE_NAME"),
#         database_user = os.getenv("DATABASE_USER"),
#         database_password = os.getenv("DATABASE_PASSWORD"),
#         host=f"/cloudsql/codet-dev-d5157:us-central1:unicornstartup-dev",  # Unix socket path
#         # port="5432"  # optional
#     )
