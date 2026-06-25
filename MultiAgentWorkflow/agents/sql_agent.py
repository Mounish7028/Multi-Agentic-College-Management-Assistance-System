import os
import re
from datetime import datetime, timedelta
from agents.llm_provider import get_llm

SCHEMA_DESCRIPTION = """
Database Schema:
1. Students (student_id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT, department TEXT, semester INTEGER)
2. Faculty (faculty_id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT, designation TEXT)
3. Courses (course_id TEXT PRIMARY KEY, course_name TEXT NOT NULL, credits INTEGER)
4. Course_Registrations (registration_id INTEGER PRIMARY KEY, student_id TEXT, course_id TEXT, status TEXT) 
   -- status can be 'Completed', 'Enrolled', 'Pending'
5. Prerequisites (prerequisite_id INTEGER PRIMARY KEY, course_id TEXT, prerequisite_course_id TEXT)
6. Attendance (attendance_id INTEGER PRIMARY KEY, student_id TEXT, course_id TEXT, classes_attended INTEGER, total_classes INTEGER)
7. Results (result_id INTEGER PRIMARY KEY, student_id TEXT, course_id TEXT, grade TEXT, marks INTEGER)
8. Leave_Requests (leave_id INTEGER PRIMARY KEY, student_id TEXT, faculty_id TEXT, date TEXT, reason TEXT, status TEXT)
   -- status can be 'Pending', 'Approved', 'Rejected'
9. Classrooms (classroom_id TEXT PRIMARY KEY, room_name TEXT NOT NULL, capacity INTEGER)
10. Classroom_Bookings (booking_id INTEGER PRIMARY KEY, classroom_id TEXT, faculty_id TEXT, booking_date TEXT, start_time TEXT, end_time TEXT)
"""

SYSTEM_PROMPT_TEMPLATE = """You are a highly professional SQLite database expert.
Your job is to translate a user's natural language request into a single executable SQLite query.

{schema_info}

Context Information:
- Current User ID: {user_id}
- Current User Role: {user_role}
- Current User Name: {user_name}
- Today's Date: {today_date}
- Tomorrow's Date: {tomorrow_date}

Strict Security Constraints:
1. If the user is a 'student' (role = student):
   - You MUST enforce that the query only reads/writes data belonging to this student.
   - For queries on Students, Attendance, Results, Leave_Requests, Course_Registrations: always add a WHERE clause checking `student_id = '{user_id}'`.
   - Never allow students to write, delete or update anything other than submitting their own Leave_Requests or booking a course (inserting into Course_Registrations).
   - If a student asks to modify their attendance, generate a SELECT query that returns 'UNAUTHORIZED' or a static message (do not generate an UPDATE query for attendance).
2. If the user is 'faculty' (role = faculty):
   - Faculty can run SELECT queries on Students, Attendance, Results, etc. to view student info, but should NOT modify student attendance or grades.
   - Faculty can insert/update classroom bookings or approve/reject leave requests. For actions like Approve/Reject leave, restrict it to leaves assigned to this faculty, i.e., `faculty_id = '{user_id}'`.

SQL Generation Rules:
- Return ONLY the SQL query. Do not write any explanations, markdown text, or introductions.
- Format the SQL code inside a markdown block:
  ```sql
  <YOUR_SQL_QUERY_HERE>
  ```
- If the request cannot be translated to a valid SQL query or violates safety, return:
  ```sql
  SELECT 'ERROR: Invalid request' AS message;
  ```
- Ensure all string comparisons are case-insensitive or correct casing (e.g., using LIKE or exact match based on schema details).
- Use correct column names and table names exactly as described.
"""

def generate_sql(query: str, user_role: str, user_id: str, user_name: str, error_feedback: str = None) -> str:
    """
    Translates a natural language query into an SQLite query.
    If error_feedback is provided, includes it in the prompt to allow correction.
    """
    llm = get_llm()
    
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        schema_info=SCHEMA_DESCRIPTION,
        user_id=user_id,
        user_role=user_role,
        user_name=user_name,
        today_date=today,
        tomorrow_date=tomorrow
    )
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    user_content = f"User Request: {query}"
    if error_feedback:
        user_content += f"\n\nPrevious attempt failed. Feedback/Error:\n{error_feedback}\n\nPlease fix the query and try again."
        
    messages.append({"role": "user", "content": user_content})
    
    try:
        response = llm.invoke(messages)
        raw_response = response.content.strip()
        print(f"[SQL Query Agent] Generated output:\n{raw_response}")
        return extract_sql(raw_response)
    except Exception as e:
        print(f"[SQL Query Agent] Error calling Ollama: {e}")
        return "SELECT 'ERROR: LLM execution failed' AS message;"

def extract_sql(text: str) -> str:
    """Extracts SQL code from markdown blocks if present, otherwise returns raw text."""
    # Find block like ```sql ... ```
    pattern = r"```sql\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
        
    # Check if there is generic ``` ... ``` block
    pattern_generic = r"```\s*(.*?)\s*```"
    match_generic = re.search(pattern_generic, text, re.DOTALL)
    if match_generic:
        return match_generic.group(1).strip()
        
    return text.strip()

if __name__ == "__main__":
    # Test cases
    print("Testing Student Query 1:")
    q1 = generate_sql("What is my attendance percentage?", "student", "S101", "Alice Smith")
    print(f"Extracted SQL:\n{q1}\n")
    
    print("Testing Student Query 2:")
    q2 = generate_sql("Submit a leave request for tomorrow.", "student", "S101", "Alice Smith")
    print(f"Extracted SQL:\n{q2}\n")
    
    print("Testing Faculty Query 1:")
    q3 = generate_sql("Show students enrolled in AI Fundamentals", "faculty", "F201", "Dr. John Doe")
    print(f"Extracted SQL:\n{q3}\n")
    
    print("Testing Faculty Query 2:")
    q4 = generate_sql("Approve leave requests submitted today.", "faculty", "F201", "Dr. John Doe")
    print(f"Extracted SQL:\n{q4}\n")
