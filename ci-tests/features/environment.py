import psycopg
from psycopg_pool import ConnectionPool

def before_all(context):
    """
    Runs once before any features or steps are executed.
    Initializes the PostgreSQL connection pool using hardcoded configurations.
    """
    print("Initializing PostgreSQL Connection Pool...")

    try:

        leaf_db_config = {
            "host": "postgres_db",
            "dbname": "your_db_name",
            "user": "postgres",
            "password": "your_password",
            "port": 5432  # Can be an integer or a string "5432"
        }


        # Initialize a ThreadedConnectionPool (best for testing environments)
        context.leaf_db_pool = ConnectionPool(
            conninfo=leaf_db_config,   # Pass the dictionary here
            min_size=1,
            max_size=10,
            open=True
        )
        print("PostgreSQL Connection Pool initialized successfully.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error while connecting to PostgreSQL: {error}")
        raise error


def after_all(context):
    """
    Runs once after all features and steps have completed.
    Closes all connections in the pool.
    """
    print("Stopping Connection Pools Connection Pool...")
    
    if hasattr(context, 'db_pool') and context.db_pool:
        # Close all connections held by the pool to prevent resource leaks
        context.db_pool.closeall()
        print("PostgreSQL Connection Pool closed.")