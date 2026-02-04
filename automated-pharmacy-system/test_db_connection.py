import mysql.connector

passwords = ['', 'root', 'password', 'admin', '123456']

for pwd in passwords:
    try:
        print(f"Testing password: '{pwd}' ...")
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password=pwd
        )
        if conn.is_connected():
            print(f"SUCCESS! Password is: '{pwd}'")
            conn.close()
            break
    except mysql.connector.Error as err:
        print(f"Failed: {err}")
