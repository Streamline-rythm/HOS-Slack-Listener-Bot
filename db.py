import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

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
    connection = pool.get_connection()
    print("✅ Successfully connected to the database")
    connection.close()
except mysql.connector.Error as err:
    print(f"❌ Failed to connect to the database: {err}")

__all__ = ["pool"]