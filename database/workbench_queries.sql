-- 🎓 Eduvision MySQL Workbench Query Examples
-- Copy and run these queries in MySQL Workbench

-- ==================== BASIC DATA VIEWING ====================

-- 1. View all sections
SELECT 
    section_id,
    section_name,
    department,
    year,
    total_students,
    created_at
FROM sections
ORDER BY section_name;

-- 2. View all students with their sections
SELECT 
    s.roll_number,
    s.name,
    s.email,
    s.mobile,
    s.section_id,
    sec.section_name,
    s.department,
    s.year
FROM students s
LEFT JOIN sections sec ON s.section_id = sec.section_id
ORDER BY s.section_id, s.roll_number;

-- 3. View all users (faculty and students)
SELECT 
    username,
    user_type,
    faculty_name,
    sections,
    created_at
FROM users
ORDER BY user_type, username;

-- ==================== ATTENDANCE REPORTS ====================

-- 4. Today's attendance by section
SELECT 
    a.section_id,
    sec.section_name,
    a.subject,
    COUNT(*) as total_marked,
    SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
    SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count,
    ROUND((SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as attendance_percentage
FROM attendance a
LEFT JOIN sections sec ON a.section_id = sec.section_id
WHERE DATE(a.attendance_date) = CURDATE()
GROUP BY a.section_id, a.subject
ORDER BY a.section_id;

-- 5. Student attendance history (last 30 days)
SELECT 
    s.name,
    s.roll_number,
    a.attendance_date,
    a.subject,
    a.status,
    a.attendance_type,
    a.marked_at
FROM attendance a
JOIN students s ON a.student_roll = s.roll_number
WHERE a.attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
ORDER BY a.attendance_date DESC, s.roll_number;

-- 6. Attendance percentage by student (this month)
SELECT 
    s.roll_number,
    s.name,
    s.section_id,
    COUNT(*) as total_classes,
    SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
    ROUND((SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as percentage
FROM attendance a
JOIN students s ON a.student_roll = s.roll_number
WHERE MONTH(a.attendance_date) = MONTH(CURDATE()) 
  AND YEAR(a.attendance_date) = YEAR(CURDATE())
GROUP BY s.roll_number, s.name, s.section_id
HAVING percentage < 75  -- Show students with less than 75% attendance
ORDER BY percentage ASC;

-- ==================== ONLINE SESSION REPORTS ====================

-- 7. Active online sessions
SELECT 
    os.session_id,
    os.faculty_username,
    os.section_id,
    sec.section_name,
    os.subject,
    os.class_type,
    os.duration_minutes,
    os.start_time,
    os.status,
    os.present_students,
    os.jitsi_link
FROM online_sessions os
LEFT JOIN sections sec ON os.section_id = sec.section_id
WHERE os.status = 'active'
ORDER BY os.start_time DESC;

-- 8. Online session attendance responses
SELECT 
    os.session_id,
    os.subject,
    os.section_id,
    or_resp.student_roll,
    s.name as student_name,
    or_resp.response,
    or_resp.response_method,
    or_resp.response_time,
    or_resp.popup_question
FROM online_sessions os
LEFT JOIN online_responses or_resp ON os.session_id = or_resp.session_id
LEFT JOIN students s ON or_resp.student_roll = s.roll_number
WHERE DATE(os.start_time) = CURDATE()  -- Today's sessions
ORDER BY os.start_time DESC, or_resp.response_time DESC;

-- 9. Online vs Offline attendance comparison
SELECT 
    section_id,
    attendance_type,
    COUNT(*) as total_records,
    SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present_count,
    ROUND((SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as percentage
FROM attendance
WHERE attendance_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)  -- Last 7 days
GROUP BY section_id, attendance_type
ORDER BY section_id, attendance_type;

-- ==================== TIMETABLE QUERIES ====================

-- 10. Today's timetable
SELECT 
    t.section_id,
    sec.section_name,
    t.start_time,
    t.end_time,
    t.subject,
    t.faculty_name,
    t.room_number,
    t.class_type
FROM timetable t
LEFT JOIN sections sec ON t.section_id = sec.section_id
WHERE t.day_of_week = DAYNAME(CURDATE())
ORDER BY t.section_id, t.start_time;

-- ==================== STATISTICS & ANALYTICS ====================

-- 11. Section-wise attendance statistics
SELECT 
    sec.section_name,
    sec.total_students,
    COUNT(DISTINCT a.student_roll) as students_with_attendance,
    COUNT(*) as total_attendance_records,
    SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as total_present,
    ROUND((SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as overall_percentage
FROM sections sec
LEFT JOIN attendance a ON sec.section_id = a.section_id
WHERE a.attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY sec.section_id, sec.section_name, sec.total_students
ORDER BY overall_percentage DESC;

-- 12. Faculty-wise online session statistics
SELECT 
    u.faculty_name,
    COUNT(os.session_id) as total_sessions,
    AVG(os.duration_minutes) as avg_duration,
    SUM(os.present_students) as total_attendance,
    AVG(os.present_students) as avg_attendance_per_session
FROM users u
LEFT JOIN online_sessions os ON u.username = os.faculty_username
WHERE u.user_type = 'faculty'
  AND os.start_time >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY u.username, u.faculty_name
ORDER BY total_sessions DESC;

-- 13. Low attendance students alert
SELECT 
    s.roll_number,
    s.name,
    s.section_id,
    s.mobile,
    COUNT(*) as total_classes,
    SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
    ROUND((SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as percentage
FROM students s
LEFT JOIN attendance a ON s.roll_number = a.student_roll
WHERE a.attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY s.roll_number, s.name, s.section_id, s.mobile
HAVING percentage < 75  -- Less than 75% attendance
ORDER BY percentage ASC;

-- ==================== DATA MAINTENANCE ====================

-- 14. Clean up old online sessions (older than 7 days)
UPDATE online_sessions 
SET status = 'completed' 
WHERE status = 'active' 
  AND start_time < DATE_SUB(NOW(), INTERVAL 7 DAY);

-- 15. Update section student counts
UPDATE sections s 
SET total_students = (
    SELECT COUNT(*) 
    FROM students st 
    WHERE st.section_id = s.section_id
);

-- ==================== USEFUL VIEWS ====================

-- 16. Create a view for daily attendance summary
CREATE VIEW daily_attendance_summary AS
SELECT 
    a.attendance_date,
    a.section_id,
    sec.section_name,
    a.subject,
    COUNT(*) as total_marked,
    SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
    SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count,
    ROUND((SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as percentage
FROM attendance a
LEFT JOIN sections sec ON a.section_id = sec.section_id
GROUP BY a.attendance_date, a.section_id, a.subject
ORDER BY a.attendance_date DESC;

-- 17. Use the view to see recent attendance summary
SELECT * FROM daily_attendance_summary 
WHERE attendance_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
ORDER BY attendance_date DESC, section_id;

-- ==================== BACKUP QUERIES ====================

-- 18. Export attendance data to review
SELECT 
    a.attendance_date,
    a.student_roll,
    s.name as student_name,
    a.section_id,
    sec.section_name,
    a.subject,
    a.status,
    a.attendance_type,
    a.marked_by,
    a.marked_at
FROM attendance a
LEFT JOIN students s ON a.student_roll = s.roll_number
LEFT JOIN sections sec ON a.section_id = sec.section_id
WHERE a.attendance_date >= '2025-01-01'  -- Change date as needed
ORDER BY a.attendance_date DESC, a.section_id, a.student_roll;

-- ==================== TROUBLESHOOTING ====================

-- 19. Check for duplicate students
SELECT roll_number, COUNT(*) as count
FROM students
GROUP BY roll_number
HAVING COUNT(*) > 1;

-- 20. Check for orphaned attendance records
SELECT DISTINCT a.student_roll
FROM attendance a
LEFT JOIN students s ON a.student_roll = s.roll_number
WHERE s.roll_number IS NULL;

-- ==================== PERFORMANCE MONITORING ====================

-- 21. Check database table sizes
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'eduvision'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;