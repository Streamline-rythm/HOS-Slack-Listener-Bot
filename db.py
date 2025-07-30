import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import pooling

# Load environment variables from .env
load_dotenv()

# Validate neccessary env values exist
required_env_vars = ["DB_USER", "DB_PASSWORD", "DB_NAME", "INSTANCE_CONNECTION_NAME"]
for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")

# Create a connection pool
pool = pooling.MySQLConnectionPool(
    pool_name="cloudsql_pool",
    pool_size=10,
    pool_reset_session=True,
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    unix_socket=f"/cloudsql/{os.getenv('INSTANCE_CONNECTION_NAME')}"
)

# Test the connection
try:
    with pool.get_connection() as connection:
        print("✅ Successfully connected to the database")
except mysql.connector.Error as err:
    print(f"❌ Failed to connect to the database: {err}")

__all__ = ["pool"]