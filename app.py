from flask import Flask, render_template, request, url_for, redirect,jsonify, Response
from pymongo import MongoClient
from config import DB_URL  # Import DB_URL from config.py
from bson import ObjectId
from datetime import datetime
import csv
import io

client = MongoClient(DB_URL)  # Create database connection
db = client['students']  # Create database object
students_collection = db["students"]

app = Flask(__name__)

@app.route('/')
def index():
    student_list = db.students.find({}).sort("regNo", 1)

    students=[]
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

# Add student
@app.route('/add-student/', methods=['POST'])
def addStudent():
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

#delete students
@app.route('/delete-student/<id>/')
def deleteStudent(id):
    db.students.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('index'))

@app.route('/update-student/<id>/', methods=['GET', 'POST'])
def editStudent(id):
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

@app.route('/login/', methods=['GET', 'POST'])
def user_login():
    return render_template('user_login.html')

@app.route('/register/', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        name_of_college = request.form['college']
        place = request.form['place']
        country = request.form['country']

        # TODO: add validation for existing users
        # TODO: adding password encryption

        user = {
            'email': email,
            'password': password,
            'phone': phone,
            'name_of_college': name_of_college,
            'place': place,
            'country': country
        }

        db.users.insert_one(user)
        return redirect(url_for('user_login'))

    return render_template('user_register.html')

# Attendance Page
@app.route('/attendance/')
def attendance_page():
    student_list = list(db.students.find({}).sort("regNo", 1))
    return render_template('attendance.html', student_list=student_list)

# Mark Attendance
@app.route('/attendance/', methods=['POST'])
def mark_attendance():
    data = request.json
    if not isinstance(data, list):
        return jsonify({"error": "Invalid data format"}), 400

    for record in data:
        student_id = record.get('student_id')
        date = datetime.strptime(record.get('date'), "%Y-%m-%d")
        status = record.get('status')
        subject = record.get('subject')
        period = record.get('period')

        student = db.students.find_one({"_id": ObjectId(student_id)})

        if student:
            attendance = student.get('attendance', {})
            subject_data = attendance.get(subject, {'total': 0, 'attended': 0})
            subject_data['total'] += 1
            if status == "Present":
                subject_data['attended'] += 1
            attendance[subject] = subject_data

            db.students.update_one(
                {"_id": ObjectId(student_id)},
                {"$set": {"attendance": attendance}}
            )

            db.attendance.insert_one({
                "student_id": ObjectId(student_id),
                "date": date,
                "subject": subject,
                "period": period,
                "status": status
            })

    return jsonify({"message": "Attendance recorded successfully!"}), 200

@app.route('/get-student/<reg_no>', methods=['GET'])
def get_student(reg_no):
    student = db.students.find_one({"regNo": reg_no})

    if not student:
        return jsonify({"error": "Student not found"}), 404

    attendance_records = list(db.attendance.find({"student_id": student["_id"]}))
    
    subject_wise = {}
    for record in attendance_records:
        subject = record.get("subject", "Unknown") 
        if subject not in subject_wise:
            subject_wise[subject] = {"total": 0, "attended": 0}

        subject_wise[subject]["total"] += 1
        if record.get("status") == "Present":
            subject_wise[subject]["attended"] += 1

    total_attended = sum(data["attended"] for data in subject_wise.values())
    total_classes = sum(data["total"] for data in subject_wise.values())
    overall_attendance = (total_attended / total_classes * 100) if total_classes else 100.0

    return jsonify({
        "name": student.get("name", "Unknown"),
        "overall_attendance": round(overall_attendance, 2),
        "subject_wise": subject_wise,
        "attendance_records": [{
            "subject": rec.get("subject", "Unknown"),
            "date": rec.get("date", "").strftime("%Y-%m-%d") if rec.get("date") else "Unknown",
            "period": rec.get("period", "Unknown"),
            "status": rec.get("status", "Unknown")
        } for rec in attendance_records]
    })

@app.route('/students/', methods=['GET', 'POST'])
def students_page():
    student = None
    subject_wise = {}
    overall_attendance = 0
    attendance_records = []

    if request.method == 'POST':
        reg_no = request.form.get('regNo')
        student = db.students.find_one({"regNo": reg_no})

        if student:
            attendance = student.get('attendance', {})
            subject_wise = {subject: {"total": data.get("total", 0), "attended": data.get("attended", 0)}
                            for subject, data in attendance.items()}
            
            valid_attendance = [att for att in attendance.values() if att.get("total", 0) > 0]
            overall_attendance = round(
                sum(att["attended"] / att["total"] * 100 for att in valid_attendance) / len(valid_attendance),
                2
            ) if valid_attendance else 100.0

            attendance_records = list(db.attendance.find({"student_id": student["_id"]}))
    
    return render_template('students.html', student=student, subject_wise=subject_wise, 
                           overall_attendance=overall_attendance, attendance_records=attendance_records)
@app.route('/export/')
def export_data():
    students = db.students.find({})
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Register Number', 'Class', 'Email', 'Phone'])  # Header
    
    for student in students:
        writer.writerow([student['name'], student['regNo'], student['class'], student['email'], student['phone']])
    
    output.seek(0)
    
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=students.csv"})



@app.route('/remark')
def remark():
    student_list = list(students_collection.find())

    for student in student_list:
        student["_id"] = str(student["_id"])  # Convert ObjectId to string for rendering
        if "remark" in student:
            for remark in student["remark"]:
                remark["date"] = remark["date"].strftime('%Y-%m-%d')  # Format date

    return render_template('remark.html', student_list=student_list)

@app.route('/add-Remark', methods=['POST'])
def add_remark():
    data = request.json  # Get data from frontend

    regNo = data.get("regNo")
    title = data.get("title")
    description = data.get("description")
    date = data.get("date")
    category = data.get("category")

    # Validate required fields
    if not all([regNo, title, description, date, category]):
        return jsonify({"error": "All fields are required!"}), 400

    # Find the student by regNo
    student = students_collection.find_one({"regNo": regNo})
    if not student:
        return jsonify({"error": "Student not found!"}), 404

    # Create remark entry
    new_remark = {
        "title": title,
        "description": description,
        "date": datetime.strptime(date, "%Y-%m-%d"),  # Convert string to date
        "category": category
    }

    # Add the remark to the student's remark list
    students_collection.update_one(
        {"_id": student["_id"]},
        {"$push": {"remark": new_remark}}
    )

    return jsonify({"message": "Remark added successfully!"}), 200

@app.route('/delete-remark', methods=['DELETE'])
def delete_remark():
    data = request.json  # Get JSON data from frontend

    regNo = data.get("regNo")  # Get the student's register number
    title = data.get("title")  # Get the remark title

    # Find the student
    student = students_collection.find_one({"regNo": regNo})

    if not student:
        return jsonify({"error": "Student not found!"}), 404

    # Remove the specific remark
    students_collection.update_one(
        {"_id": student["_id"]},
        {"$pull": {"remark": {"title": title}}}  # Remove remark with matching title
    )

    return jsonify({"message": "Remark deleted successfully!"}), 200

if __name__ == '__main__':
    app.run(debug=True)

