import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import pooling

# Load environment variables from .env (optional in Cloud Run, helpful locally)
load_dotenv()

# Ensure required environment variables are set
required_env_vars = ["DB_USER", "DB_PASSWORD", "DB_NAME", "INSTANCE_CONNECTION_NAME"]
for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")

# Create connection pool using Cloud SQL Unix socket
pool = pooling.MySQLConnectionPool(
    pool_name="cloudsql_pool",
    pool_size=10,
    pool_reset_session=True,
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    unix_socket=f"/cloudsql/{os.getenv('INSTANCE_CONNECTION_NAME')}"
)

# Optional: test the connection
try:
    with pool.get_connection() as conn:
        print("✅ Successfully connected to the Cloud SQL database")
except mysql.connector.Error as err:
    print(f"❌ Failed to connect to Cloud SQL: {err}")

__all__ = ["pool"]
