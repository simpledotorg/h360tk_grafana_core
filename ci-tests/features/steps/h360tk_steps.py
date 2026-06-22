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



@given('The following facility exists:')
def step_impl(context):
    pool = context.leaf_db_pool
    parent_id = None 
    context.created_hierarchy = []
    
    try:
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                for row in context.table:
                    facility_name = row['name']
                    
                    # 1. Check if the tier already exists.
                    # We look up based on name and parent_id.
                    if parent_id is None:
                        select_query = "SELECT id, level FROM org_units WHERE name = %s AND parent_id IS NULL LIMIT 1;"
                        cursor.execute(select_query, (facility_name,))
                    else:
                        select_query = "SELECT id, level FROM org_units WHERE name = %s AND parent_id = %s LIMIT 1;"
                        cursor.execute(select_query, (facility_name, parent_id))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        current_id = result[0]
                        current_level = result[1]
                    else:
                        # 2. If it doesn't exist, we INSERT it.
                        # Instead of calculating 'level' in Python, we query the parent's level 
                        # directly in the SQL statement. If parent_id is NULL, it falls back to 1.
                        insert_query = """
                            INSERT INTO org_units (name, parent_id, level) 
                            VALUES (
                                %s, 
                                %s, 
                                COALESCE((SELECT level + 1 FROM org_units WHERE id = %s), 1)
                            ) 
                            RETURNING id, level;
                        """
                        cursor.execute(insert_query, (facility_name, parent_id, parent_id))
                        
                        inserted_result = cursor.fetchone()
                        current_id = inserted_result[0]
                        current_level = inserted_result[1]
                    
                    # Save the real database values to the context tracking list
                    context.created_hierarchy.append({
                        "id": current_id,
                        "name": facility_name,
                        "parent_id": parent_id,
                        "level": current_level
                    })
                    
                    # Move down to the next child item
                    parent_id = current_id
                    
    except Exception as e:
        raise AssertionError(f"Failed to process facility hierarchy idempotently: {e}")

