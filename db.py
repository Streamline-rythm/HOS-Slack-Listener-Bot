import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import pooling

# Load environment variables from .env
load_dotenv()

# Validate required env variables
required_vars = ["DB_USER", "DB_PASSWORD", "DB_NAME", "ENV"]
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")

env_mode = os.getenv("ENV")

# Build connection settings based on environment
if env_mode == "production":
    if not os.getenv("INSTANCE_CONNECTION_NAME"):
        raise ValueError("Missing INSTANCE_CONNECTION_NAME for production mode")
    conn_settings = {
        "unix_socket": f"/cloudsql/{os.getenv('INSTANCE_CONNECTION_NAME')}"
    }
else:
    # Default to local TCP connection
    conn_settings = {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", 3306)),
    }

# Create connection pool
pool = pooling.MySQLConnectionPool(
    pool_name="hos_pool",
    pool_size=10,
    pool_reset_session=True,
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    **conn_settings
)

# Optional: Test the connection
try:
    with pool.get_connection() as conn:
        print("✅ Successfully connected to the database.")
except mysql.connector.Error as err:
    print(f"❌ Failed to connect to the database: {err}")

__all__ = ["pool"]
