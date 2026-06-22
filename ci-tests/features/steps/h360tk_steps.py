from behave import given, when, then

# A simple class to simulate the application code we are testing
class H360tkSteps:
    def __init__(self):
        self.current_facility_id  = None



@given('I create a new facility with name "{facility_name}"')
def step_impl(context, facility_name):
    pool = context.leaf_db_pool
    try:
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                
                # --- Run the SELECT query ---
                select_query = "SELECT id, name FROM users WHERE id = %s;"
                cursor.execute(select_query, (1,))
                user_record = cursor.fetchone()
                print("Select Result:", user_record)
                
                # --- Run the INSERT query ---
                insert_query = "INSERT INTO users (name, email) VALUES (%s, %s);"
                cursor.execute(insert_query, ("Bob", "bob@example.com"))
                print("Insert query executed successfully")
                
                # Note: Do NOT call conn.commit() manually here. 
                # Psycopg 3's `with pool.connection()` context block manages the commit automatically 
                # as soon as execution exits this indentation block cleanly.

        print("Transaction committed automatically and connection returned to the pool.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise
