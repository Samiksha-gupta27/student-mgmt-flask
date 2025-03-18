from flask import Flask, render_template, request, url_for, redirect, jsonify
from pymongo import MongoClient
from config import DB_URL
from bson import ObjectId
from datetime import datetime

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

@app.route('/add-student/', methods=['POST'])
def addStudent():
    data = request.form
    db.students.insert_one({
        'name': data['name'],
        'regNo': data['registerNumber'],
        'class': data['class'],
        'email': data['email'],
        'phone': data['phone'],
        'club': data.get('club', "No Club"),
        'role': data.get('role', "Member"),
        'attendance': {}
    })
    return redirect(url_for('index'))

@app.route('/delete-student/<id>/')
def deleteStudent(id):
    db.students.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('index'))

@app.route('/update-student/<id>/', methods=['POST'])
def editStudent(id):
    name = request.form['name']
    regNo = request.form['registerNumber']
    st_class = request.form['class']
    email = request.form['email']
    phone = request.form['phone']
    club = request.form.get('club', "No Club")
    role = request.form.get('role', "Member")

    db.students.update_one({'_id': ObjectId(id)}, {
        '$set': {
            'name': name,
            'regNo': regNo,
            'class': st_class,
            'email': email,
            'phone': phone,
            'club': club,
            'role': role
        }
    })
    return redirect(url_for('index'))

@app.route('/clubs/')
def clubs_page():
    return render_template('clubs.html')

@app.route('/get-club-member/<reg_no>', methods=['GET'])
def get_club_member(reg_no):
    student = db.students.find_one({"regNo": reg_no})
    if not student:
        return jsonify({"error": "Student not found"}), 404
    
    meeting_records = list(db.club_attendance.find({"student_id": student["_id"]}))
    return jsonify({
        "name": student.get("name", "Unknown"),
        "club": student.get("club", "No Club"),
        "role": student.get("role", "Member"),
        "meeting_records": [{
            "date": rec.get("date", "Unknown"),
            "status": rec.get("status", "Unknown")
        } for rec in meeting_records]
    })

@app.route('/mark-meeting-attendance/', methods=['POST'])
def mark_meeting_attendance():
    data = request.json
    reg_no = data.get('regNo')
    status = data.get('status')
    student = db.students.find_one({"regNo": reg_no})
    
    if not student:
        return jsonify({"error": "Student not found"}), 404

    db.club_attendance.insert_one({
        "student_id": student["_id"],
        "date": datetime.now().strftime("%Y-%m-%d"),
        "status": status
    })
    return jsonify({"message": "Attendance recorded successfully!"}), 200

@app.route('/attendance/')
def attendance_page():
    student_list = list(db.students.find({}).sort("regNo", 1))
    return render_template('attendance.html', student_list=student_list)

@app.route('/students/')
def students_page():
    student_list = db.students.find({}).sort("regNo", 1)
    return render_template('students.html', student_list=student_list)
git init


if __name__ == '__main__':
    app.run(debug=True)
