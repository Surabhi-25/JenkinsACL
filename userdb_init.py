import psycopg2
from app import get_db_connection # Assuming get_db_connection is in your main file

def initialize_s3_users_table():
    """Connects to RDS and creates the s3_users table and index."""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            print("ERROR: Failed to establish database connection.")
            return

        cur = conn.cursor()

        # SQL to create the table and index (identical to your provided SQL)
        sql_commands = """
        -- 1. Create the s3_users table
        CREATE TABLE IF NOT EXISTS s3_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            canonical_id VARCHAR(250) UNIQUE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- 2. Add an index for faster lookups by username
        CREATE INDEX IF NOT EXISTS idx_s3_users_username ON s3_users (username);
        
        -- 3. Example data (Optional, remove if you don't want test data)
        INSERT INTO s3_users (username, canonical_id) 
        VALUES ('test_user', '79a59df900b949e55d96a1e698fbacedfd6e09d98eacf8f8d5218e7cd47ef2be')
        ON CONFLICT (username) DO NOTHING;
        """
        
        # Execute multiple commands
        cur.execute(sql_commands)
        conn.commit()
        cur.close()
        print("✅ Success: The 's3_users' table and index have been created/verified in RDS.")

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"❌ Database error during initialization: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    initialize_s3_users_table()

# NOTE: You must run this script once from a machine that can access your RDS instance.