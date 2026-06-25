import os
from database import get_connection, init_db

def seed_data():
    # Make sure tables exist
    init_db()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Clear existing data in reverse order of foreign keys
    cursor.execute("DELETE FROM Classroom_Bookings;")
    cursor.execute("DELETE FROM Leave_Requests;")
    cursor.execute("DELETE FROM Results;")
    cursor.execute("DELETE FROM Attendance;")
    cursor.execute("DELETE FROM Prerequisites;")
    cursor.execute("DELETE FROM Course_Registrations;")
    cursor.execute("DELETE FROM Classrooms;")
    cursor.execute("DELETE FROM Courses;")
    cursor.execute("DELETE FROM Faculty;")
    cursor.execute("DELETE FROM Students;")
    
    # 1. Insert Students
    students = [
        ('S101', 'Alice Smith', 'alice@college.edu', 'password123', 'Computer Science', 4),
        ('S102', 'Bob Jones', 'bob@college.edu', 'password123', 'Computer Science', 4),
        ('S103', 'Charlie Brown', 'charlie@college.edu', 'password123', 'Mechanical Engineering', 2),
        ('S104', 'Diana Prince', 'diana@college.edu', 'password123', 'Information Technology', 6)
    ]
    cursor.executemany("INSERT INTO Students (student_id, name, email, password, department, semester) VALUES (?, ?, ?, ?, ?, ?);", students)
    
    # 2. Insert Faculty
    faculty = [
        ('F201', 'Dr. John Doe', 'johndoe@college.edu', 'password123', 'Professor'),
        ('F202', 'Dr. Sarah Connor', 'sarahconnor@college.edu', 'password123', 'Associate Professor'),
        ('F203', 'Dr. Alan Turing', 'turing@college.edu', 'password123', 'Professor')
    ]
    cursor.executemany("INSERT INTO Faculty (faculty_id, name, email, password, designation) VALUES (?, ?, ?, ?, ?);", faculty)
    
    # 3. Insert Courses
    courses = [
        ('CS201', 'Data Structures', 4),
        ('CS202', 'Algorithms', 4),
        ('CS301', 'AI Fundamentals', 3),
        ('CS302', 'Machine Learning', 4),
        ('ME101', 'Thermodynamics', 4)
    ]
    cursor.executemany("INSERT INTO Courses (course_id, course_name, credits) VALUES (?, ?, ?);", courses)
    
    # 4. Insert Prerequisites
    prereqs = [
        (1, 'CS202', 'CS201'), # Algorithms requires Data Structures
        (2, 'CS302', 'CS201')  # Machine Learning requires Data Structures
    ]
    cursor.executemany("INSERT INTO Prerequisites (prerequisite_id, course_id, prerequisite_course_id) VALUES (?, ?, ?);", prereqs)
    
    # 5. Insert Course Registrations
    registrations = [
        (1, 'S101', 'CS201', 'Completed'),
        (2, 'S101', 'CS202', 'Enrolled'),
        (3, 'S101', 'CS301', 'Pending'),
        (4, 'S102', 'CS201', 'Enrolled'),
        (5, 'S102', 'CS301', 'Enrolled'),
        (6, 'S103', 'ME101', 'Enrolled'),
        (7, 'S104', 'CS301', 'Enrolled'),
        (8, 'S104', 'CS302', 'Enrolled')
    ]
    cursor.executemany("INSERT INTO Course_Registrations (registration_id, student_id, course_id, status) VALUES (?, ?, ?, ?);", registrations)
    
    # 6. Insert Attendance
    attendance = [
        (1, 'S101', 'CS202', 26, 30), # Alice: CS202 (86.67%)
        (2, 'S101', 'CS301', 10, 10), # Alice: CS301 (100%)
        (3, 'S102', 'CS201', 20, 30), # Bob: CS201 (66.67%)
        (4, 'S102', 'CS301', 25, 30), # Bob: CS301 (83.33%)
        (5, 'S103', 'ME101', 28, 30), # Charlie: ME101 (93.33%)
        (6, 'S104', 'CS301', 22, 30), # Diana: CS301 (73.33%)
        (7, 'S104', 'CS302', 29, 30)  # Diana: CS302 (96.67%)
    ]
    cursor.executemany("INSERT INTO Attendance (attendance_id, student_id, course_id, classes_attended, total_classes) VALUES (?, ?, ?, ?, ?);", attendance)
    
    # 7. Insert Results
    results = [
        (1, 'S101', 'CS201', 'A', 92),
        (2, 'S102', 'CS201', 'B', 81),
        (3, 'S104', 'CS302', 'A', 95),
        (4, 'S101', 'CS302', 'A+', 98)
    ]
    cursor.executemany("INSERT INTO Results (result_id, student_id, course_id, grade, marks) VALUES (?, ?, ?, ?, ?);", results)
    
    # 8. Insert Leave Requests
    # Note: We need a leave request ID 23 to demonstrate rejection
    # We will use manual primary key values to ensure leave_id 23 is created.
    leave_requests = [
        (23, 'S101', 'F201', '2026-06-18', 'Medical Checkup', 'Pending'),
        (24, 'S102', 'F201', '2026-06-17', 'Family Event', 'Pending'),
        (25, 'S103', 'F202', '2026-06-17', 'Sick Leave', 'Pending')
    ]
    cursor.executemany("INSERT INTO Leave_Requests (leave_id, student_id, faculty_id, date, reason, status) VALUES (?, ?, ?, ?, ?, ?);", leave_requests)
    
    # 9. Insert Classrooms
    classrooms = [
        ('C101', 'Lab-302', 60),
        ('C102', 'Room-101', 40),
        ('C103', 'Seminar Hall', 120)
    ]
    cursor.executemany("INSERT INTO Classrooms (classroom_id, room_name, capacity) VALUES (?, ?, ?);", classrooms)
    
    # 10. Insert Classroom Bookings
    bookings = [
        (1, 'C102', 'F201', '2026-06-17', '10:00', '12:00'),
        (2, 'C103', 'F202', '2026-06-17', '14:00', '16:00')
    ]
    cursor.executemany("INSERT INTO Classroom_Bookings (booking_id, classroom_id, faculty_id, booking_date, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?);", bookings)
    
    conn.commit()
    conn.close()
    print("Database seeded with sample data.")

if __name__ == "__main__":
    seed_data()
