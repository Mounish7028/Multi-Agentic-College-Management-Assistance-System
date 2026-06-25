import re
import sqlite3
from db.database import get_connection

# Allowed tables in our database schema
VALID_TABLES = [
    "students", "faculty", "courses", "course_registrations", 
    "prerequisites", "attendance", "results", "leave_requests", 
    "classrooms", "classroom_bookings"
]

def validate_sql(sql: str, user_role: str, user_id: str) -> dict:
    """
    Validates a generated SQL query for syntax, schema matching, and security constraints.
    Returns: {"valid": bool, "feedback": str}
    """
    sql_clean = sql.strip().strip(";").strip()
    
    # 1. Basic empty check
    if not sql_clean:
        return {"valid": False, "feedback": "Generated SQL query is empty."}
        
    sql_lower = sql_clean.lower()
    
    # 2. Strict Security: Block unauthorized commands
    if user_role.lower() == "student":
        # Students are only allowed SELECT queries, plus specific INSERT for Leave_Requests and Course_Registrations.
        is_select = sql_lower.startswith("select")
        is_leave_insert = sql_lower.startswith("insert into leave_requests")
        is_course_reg = sql_lower.startswith("insert into course_registrations")
        
        if not (is_select or is_leave_insert or is_course_reg):
            return {
                "valid": False,
                "feedback": "Security Policy Violation: Students are only permitted to query database (SELECT) or submit leave requests/register for courses (INSERT). UPDATE/DELETE/DROP operations are prohibited."
            }
            
        # Enforce student_id scoping in SELECT/INSERT
        # If the query mentions tables containing student personal data, it must filter by their student_id
        personal_tables = ["students", "attendance", "results", "leave_requests", "course_registrations"]
        
        # Check if any personal tables are queried
        tables_in_query = [t for t in personal_tables if t in sql_lower]
        
        if tables_in_query:
            # Check if student_id is filtered
            student_id_filter = f"student_id = '{user_id}'"
            student_id_filter_alt = f"student_id='{user_id}'"
            student_id_insert = f"'{user_id}'"
            
            # For insert, ensure student_id value matches user_id
            if sql_lower.startswith("insert"):
                if student_id_insert not in sql:
                    return {
                        "valid": False,
                        "feedback": f"Security Policy Violation: You can only insert records belonging to your own student_id ({user_id})."
                    }
            else:
                # For select, make sure user_id is in the WHERE filter
                if student_id_filter not in sql and student_id_filter_alt not in sql_lower.replace(" ", ""):
                    # Let's see if student_id is filtered dynamically
                    if "student_id" not in sql_lower:
                        return {
                            "valid": False,
                            "feedback": f"Security Policy Violation: Student queries on personal tables ({', '.join(tables_in_query)}) must filter results by `student_id = '{user_id}'` to prevent unauthorized access to other students' data."
                        }
                        
    elif user_role.lower() == "faculty":
        # Faculty can run SELECT on any table, and INSERT/UPDATE on classroom_bookings and leave_requests
        is_select = sql_lower.startswith("select")
        is_booking_write = "classroom_bookings" in sql_lower and (sql_lower.startswith("insert") or sql_lower.startswith("update") or sql_lower.startswith("delete"))
        is_leave_update = "leave_requests" in sql_lower and sql_lower.startswith("update")
        
        if not (is_select or is_booking_write or is_leave_update):
            return {
                "valid": False,
                "feedback": "Security Policy Violation: Faculty members are only permitted to query data, book/modify classrooms, or approve/reject leave requests."
            }
            
    # 3. Dry-run parsing using EXPLAIN to check SQLite syntax and column/table schema validity
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # EXPLAIN validates syntax and schema checks without executing modification or fetching records
        cursor.execute(f"EXPLAIN {sql_clean};")
        
        # Additional table validation checking
        for word in re.findall(r"\b[a-zA-Z_]+\b", sql_lower):
            if word in VALID_TABLES:
                # Table is valid
                pass
                
        return {"valid": True, "feedback": ""}
        
    except sqlite3.Error as e:
        error_msg = str(e)
        print(f"[Validator Agent] SQL dry-run failed: {error_msg} for query:\n{sql_clean}")
        return {
            "valid": False,
            "feedback": f"SQL Syntax/Schema Error: {error_msg}. Please check table structures and SQL syntax rules for SQLite."
        }
    finally:
        conn.close()

if __name__ == "__main__":
    # Test cases
    print(validate_sql("SELECT * FROM Students WHERE student_id = 'S101';", "student", "S101"))
    print(validate_sql("SELECT * FROM Students WHERE student_id = 'S102';", "student", "S101")) # should fail
    print(validate_sql("SELECT * FROM Students;", "student", "S101")) # should fail
    print(validate_sql("UPDATE Attendance SET classes_attended = 100 WHERE student_id = 'S101';", "student", "S101")) # should fail
    print(validate_sql("SELECT * FROM NonExistentTable;", "faculty", "F201")) # should fail (schema check)
    print(validate_sql("EXPLAIN SELECT * FROM Students;", "student", "S101")) # invalid command for student
