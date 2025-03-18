from flask import Flask, render_template, request, url_for, redirect, jsonify, Response
from pymongo import MongoClient
from config import DB_URL
from bson import ObjectId
import csv
import io

client = MongoClient(DB_URL)
db = client['students']

app = Flask(__name__)

@app.route('/')
def index():
    student_list = db.students.find({}).sort("regNo", 1)
    students = []

    for student in student_list:
        attendance = student.get('attendance', {})

        if not isinstance(attendance, dict):
            attendance = {}

        total_present = sum(subject.get('attended', 0) for subject in attendance.values() if isinstance(subject, dict))
        total_completed = sum(subject.get('total', 0) for subject in attendance.values() if isinstance(subject, dict))

        percentage = (total_present / total_completed) * 100 if total_completed > 0 else 0
        student['attendance_percentage'] = round(percentage, 2)

        students.append(student)

    return render_template('index.html', student_list=students)

# Add Student
@app.route('/add-student/', methods=['POST'])
def add_student():
    data = request.form
    db.students.insert_one({
        'name': data['name'],
        'regNo': data['registerNumber'],
        'class': data['class'],
        'email': data['email'],
        'phone': data['phone'],
        'attendance': {}
    })
    return redirect(url_for('index'))

# Delete Student
@app.route('/delete-student/<id>/')
def delete_student(id):
    db.students.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('index'))

# Update Student
@app.route('/update-student/<id>/', methods=['GET', 'POST'])
def edit_student(id):
    if request.method == 'GET':
        student = db.students.find_one({'_id': ObjectId(id)})
        students = db.students.find({})
        return render_template('index.html', student=student, student_list=students)
    else:
        name = request.form['name']
        regNo = request.form['registerNumber']
        st_class = request.form['class']
        email = request.form['email']
        phone = request.form['phone']

        db.students.update_one({'_id': ObjectId(id)}, {
            '$set': {
                'name': name,
                'regNo': regNo,
                'class': st_class,
                'email': email,
                'phone': phone
            }
        })
        return redirect(url_for('index'))

# Students Page (Restored)
@app.route('/students/', methods=['GET', 'POST'])
def students_page():
    student_list = list(db.students.find({}).sort("regNo", 1))
    return render_template('students.html', student_list=student_list)

# Timetable Page
@app.route('/timetable')
def timetable_page():
    return render_template('timetable.html')

# Add Course
@app.route('/add-course', methods=['POST'])
def add_course():
    data = request.json
    course_name = data.get('course_name')

    if not course_name:
        return jsonify({"error": "Course name is required"}), 400

    if db.courses.find_one({"name": course_name}):
        return jsonify({"error": "Course already exists!"}), 400

    db.courses.insert_one({"name": course_name})
    return jsonify({"message": "Course added successfully!"}), 200

# Fetch Courses
@app.route('/get-courses')
def get_courses():
    courses = list(db.courses.find({}, {"name": 1, "_id": 0}))
    return jsonify(courses)

# Add Subject with Duplicate Slot Prevention
@app.route('/add-subject', methods=['POST'])
def add_subject():
    data = request.json
    course_name = data.get('course_name')
    subject_name = data.get('subject_name')
    lecture_slot = data.get('lecture_slot')
    day = data.get('day')

    if not course_name or not subject_name or not lecture_slot or not day:
        return jsonify({"error": "All fields are required"}), 400

    existing_entry = db.timetable.find_one({"day": day, "lecture_slot": lecture_slot, "course": course_name})
    if existing_entry:
        return jsonify({"error": "A subject is already assigned to this slot for the selected course!"}), 400

    db.timetable.insert_one({
        "day": day,
        "course": course_name,
        "subject": subject_name,
        "lecture_slot": lecture_slot
    })
    return jsonify({"message": "Subject added successfully!"}), 200

# Fetch Weekly Timetable for Selected Course
@app.route('/get-weekly-timetable/<course_name>')
def get_weekly_timetable(course_name):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    slots = ["9:00-9:50", "10:00-10:50", "11:00-11:50", "12:00-12:50", "2:00-2:50", "3:00-3:50", "4:00-4:50"]

    weekly_timetable = []
    for day in days:
        row = {"day": day}
        for slot in slots:
            entry = db.timetable.find_one({"day": day, "lecture_slot": slot, "course": course_name}, {"_id": 0, "subject": 1})
            row[slot] = entry["subject"] if entry else ""
        weekly_timetable.append(row)

    return jsonify(weekly_timetable)

# Edit Timetable Entry
@app.route('/edit-subject', methods=['POST'])
def edit_subject():
    data = request.json
    day = data.get('day')
    lecture_slot = data.get('lecture_slot')
    new_subject = data.get('subject_name')
    course_name = data.get('course_name')

    if not day or not lecture_slot or not new_subject or not course_name:
        return jsonify({"error": "All fields are required"}), 400

    db.timetable.update_one(
        {"day": day, "lecture_slot": lecture_slot, "course": course_name},
        {"$set": {"subject": new_subject}}
    )
    return jsonify({"message": "Subject updated successfully!"}), 200

# Download Timetable as CSV for Selected Course
@app.route('/download-timetable/<course_name>')
def download_timetable(course_name):
    timetable = db.timetable.find({"course": course_name})
    output = io.StringIO()
    writer = csv.writer(output)

    # CSV Header
    writer.writerow(['Day', 'Course', 'Subject', 'Lecture Slot'])

    for entry in timetable:
        writer.writerow([
            entry.get('day', 'Unknown'), 
            entry.get('course', 'Unknown'), 
            entry.get('subject', 'Unknown'), 
            entry.get('lecture_slot', 'Unknown')
        ])

    output.seek(0)
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": f"attachment; filename={course_name}_timetable.csv"})


# Attendance Page
@app.route('/attendance/')
def attendance_page():
    student_list = list(db.students.find({}).sort("regNo", 1))
    return render_template('attendance.html', student_list=student_list)

# Export Student Data as CSV
@app.route('/export/')
def export_data():
    students = db.students.find({})
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Register Number', 'Class', 'Email', 'Phone', 'Attendance %'])

    for student in students:
        attendance = student.get('attendance', {})
        total_present = sum(subject.get('attended', 0) for subject in attendance.values() if isinstance(subject, dict))
        total_completed = sum(subject.get('total', 0) for subject in attendance.values() if isinstance(subject, dict))
        percentage = (total_present / total_completed) * 100 if total_completed > 0 else 0
        writer.writerow([student['name'], student['regNo'], student['class'], student['email'], student['phone'], round(percentage, 2)])

    output.seek(0)
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=students.csv"})

if __name__ == '__main__':
    app.run(debug=True)
