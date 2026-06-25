import os
import sqlite3
from dotenv import load_dotenv

# Load env variables
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/college.db")

def get_connection():
    """Establishes and returns a connection to the SQLite database."""
    # Ensure database directory exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;") # Enforce foreign key constraints
    conn.row_factory = sqlite3.Row # Return dictionary-like rows
    return conn

def init_db():
    """Creates the tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Students Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Students (
        student_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        department TEXT NOT NULL,
        semester INTEGER NOT NULL
    );
    """)
    
    # 2. Faculty Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Faculty (
        faculty_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        designation TEXT NOT NULL
    );
    """)
    
    # 3. Courses Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Courses (
        course_id TEXT PRIMARY KEY,
        course_name TEXT NOT NULL,
        credits INTEGER NOT NULL
    );
    """)
    
    # 4. Course_Registrations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Course_Registrations (
        registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        course_id TEXT NOT NULL,
        status TEXT CHECK(status IN ('Completed', 'Enrolled', 'Pending')) NOT NULL,
        FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (course_id) REFERENCES Courses(course_id) ON DELETE CASCADE
    );
    """)
    
    # 5. Prerequisites Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Prerequisites (
        prerequisite_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id TEXT NOT NULL,
        prerequisite_course_id TEXT NOT NULL,
        FOREIGN KEY (course_id) REFERENCES Courses(course_id) ON DELETE CASCADE,
        FOREIGN KEY (prerequisite_course_id) REFERENCES Courses(course_id) ON DELETE CASCADE
    );
    """)
    
    # 6. Attendance Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        course_id TEXT NOT NULL,
        classes_attended INTEGER NOT NULL,
        total_classes INTEGER NOT NULL,
        FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (course_id) REFERENCES Courses(course_id) ON DELETE CASCADE
    );
    """)
    
    # 7. Results Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Results (
        result_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        course_id TEXT NOT NULL,
        grade TEXT NOT NULL,
        marks INTEGER NOT NULL,
        FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (course_id) REFERENCES Courses(course_id) ON DELETE CASCADE
    );
    """)
    
    # 8. Leave_Requests Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Leave_Requests (
        leave_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        faculty_id TEXT NOT NULL,
        date TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT CHECK(status IN ('Pending', 'Approved', 'Rejected')) NOT NULL,
        FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (faculty_id) REFERENCES Faculty(faculty_id) ON DELETE CASCADE
    );
    """)
    
    # 9. Classrooms Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Classrooms (
        classroom_id TEXT PRIMARY KEY,
        room_name TEXT NOT NULL,
        capacity INTEGER NOT NULL
    );
    """)
    
    # 10. Classroom_Bookings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Classroom_Bookings (
        booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        classroom_id TEXT NOT NULL,
        faculty_id TEXT NOT NULL,
        booking_date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        FOREIGN KEY (classroom_id) REFERENCES Classrooms(classroom_id) ON DELETE CASCADE,
        FOREIGN KEY (faculty_id) REFERENCES Faculty(faculty_id) ON DELETE CASCADE
    );
    """)
    
    conn.commit()
    conn.close()
    print("Database tables initialized successfully.")

def execute_query(query: str, params: tuple = ()) -> list:
    """Executes a SELECT query and returns rows as dictionaries."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        return result
    except Exception as e:
        print(f"Error executing SELECT query: {e}")
        raise e
    finally:
        conn.close()

def execute_write(query: str, params: tuple = ()) -> int:
    """Executes an INSERT, UPDATE, or DELETE query and returns the lastrowid or rowcount."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        if query.strip().upper().startswith("INSERT"):
            return cursor.lastrowid
        return cursor.rowcount
    except Exception as e:
        print(f"Error executing write query: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
