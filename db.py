import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# Read credentials from environment variables (works on Render, local .env, and Streamlit Cloud)
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_USER     = os.getenv("DB_USER",     "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME     = os.getenv("DB_NAME",     "timetable_optimizer")
DB_PORT     = int(os.getenv("DB_PORT", "3306"))

def get_conn():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            database=DB_NAME,
            connection_timeout=10,
            connect_timeout=10
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Failed to connect to database: {err}")
        raise err

def execute_query(query, params=None, commit=False):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        result = cursor.lastrowid if commit else cursor.fetchall()
        if commit:
            conn.commit()
        return result
    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Query error: {err}")
        raise err
    finally:
        cursor.close()
        conn.close()

def init_db():
    """Run schema.sql to create tables if they don't exist. Safe to run multiple times."""
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with open(schema_path, "r") as f:
        schema = f.read()

    conn = get_conn()
    cursor = conn.cursor()
    for stmt in schema.split(";"):
        stmt = stmt.strip()
        if stmt:
            cursor.execute(stmt)
    conn.commit()
    cursor.close()
    conn.close()

def seed_db():
    users_count = execute_query("SELECT COUNT(*) as c FROM users")[0]['c']
    if users_count > 0:
        return

    import random
    random.seed(42)

    preftimes = ["Morning", "Afternoon", "Night"]
    for i in range(1, 21):
        u_id = execute_query(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            (f"Student {i}", f"student{i}@example.com"),
            commit=True
        )
        pref = random.choice(preftimes)
        sleep = random.choice([6.0, 7.0, 8.0, 9.0])
        gym = random.choice([0.0, 1.0, 1.5, 2.0])
        study = random.choice([2.0, 3.0, 4.0, 5.0, 6.0])

        execute_query(
            "INSERT INTO preferences (user_id, sleep_hours, gym_hours, study_hours_per_day, preferred_study_time) "
            "VALUES (%s, %s, %s, %s, %s)",
            (u_id, sleep, gym, study, pref),
            commit=True
        )

        for s in ["Math", "CS", "Physics"]:
            execute_query(
                "INSERT INTO subjects (user_id, subject_name) VALUES (%s, %s)",
                (u_id, s),
                commit=True
            )
