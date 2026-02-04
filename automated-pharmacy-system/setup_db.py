import mysql.connector

def setup_database():
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '123456' 
    }
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(buffered=True)
        
        # Use absolute path relative to this script
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file_path = os.path.join(base_dir, 'database', 'pharmacy.sql')
        
        with open(sql_file_path, 'r') as f:
            sql_script = f.read()
        
        # Split by semicolon to execute multiple statements
        statements = sql_script.split(';')
        
        for statement in statements:
            if statement.strip():
                try:
                    cursor.execute(statement)
                    print(f"Executed: {statement[:50]}...")
                except mysql.connector.Error as err:
                    print(f"Skipping/Error: {err}")
        
        conn.commit()
        print("\nDatabase setup completed successfully!")
        
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    setup_database()
