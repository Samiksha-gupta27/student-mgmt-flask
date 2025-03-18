from flask import Flask, render_template, request, url_for, redirect,jsonify, Response
from pymongo import MongoClient
from config import DB_URL  # Import DB_URL from config.py
from bson import ObjectId
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid  # To generate unique file names
import os
from flask import send_from_directory
import csv
import io

client = MongoClient(DB_URL)  # Create database connection
db = client['students']  # Create database object

app = Flask(__name__)
MEDIA_FOLDER = 'media/ProfilePicture'
app.config['MEDIA_FOLDER'] = 'media/ProfilePicture'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(app.config['MEDIA_FOLDER']):
    os.makedirs(app.config['MEDIA_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/media/<path:filename>')
def media(filename):
    return send_from_directory(app.config['MEDIA_FOLDER'], filename)

@app.route('/')
def index():
    sort_by = request.args.get("sort_by", "name_asc")
    class_filter = request.args.get("class_filter", "")

    query = {}
    if class_filter:
        query["class"] = class_filter

    sort_options = {
        "name_asc": ("name", 1),
        "name_desc": ("name", -1),
        "regNo_asc": ("regNo", 1),
        "regNo_desc": ("regNo", -1),
        "class_asc": ("class", 1),
        "class_desc": ("class", -1),
    }
    
    sort_field, sort_order = sort_options.get(sort_by, ("name", 1))

    student_list = db.students.find(query).sort(sort_field, sort_order)

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

    unique_classes = db.students.distinct("class")

    return render_template('index.html', student_list=students, unique_classes=unique_classes)

# Add student
@app.route('/add-student/', methods=['POST'])
def add_student():
    """Add a new student with profile picture upload and attendance initialization"""
    name = request.form['name']
    regNo = request.form['registerNumber']
    st_class = request.form['class']
    email = request.form['email']
    phone = request.form['phone']

    # Handle profile picture upload
    filename = "default.png"  # Default image if no file is uploaded
    if 'photo' in request.files and request.files['photo'].filename:
        file = request.files['photo']
        if file and allowed_file(file.filename):
            # Generate a unique filename
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4()}.{ext}"  
            file.save(os.path.join(app.config['MEDIA_FOLDER'], filename))

    # Insert student into database
    db.students.insert_one({
        'name': name,
        'regNo': regNo,
        'class': st_class,
        'email': email,
        'phone': phone,
        'photo': filename,  # Store profile picture filename
        'attendance': {}  # Initialize empty attendance
    })

    return redirect(url_for('index'))


#delete students
@app.route('/delete-student/<id>/',methods=['POST'])
def deleteStudent(id):
    db.students.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('index'))

@app.route('/update-student/<student_id>/', methods=['POST'])
def update_student(student_id):
    student = db.students.find_one({"_id": ObjectId(student_id)})
    
    if not student:
        return "Student not found", 404

    name = request.form.get("name")
    reg_no = request.form.get("registerNumber")
    student_class = request.form.get("class")
    email = request.form.get("email")
    phone = request.form.get("phone")

    # Handling file upload (profile picture)
    filename = student.get("photo")  # Keep existing photo if no new file uploaded
    if 'photo' in request.files and request.files['photo'].filename:
        photo = request.files['photo']
        if allowed_file(photo.filename):
            ext = photo.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4()}.{ext}"  # Unique filename
            photo.save(os.path.join(app.config['MEDIA_FOLDER'], filename))

    updated_data = {
        "name": name,
        "regNo": reg_no,
        "class": student_class,
        "email": email,
        "phone": phone,
        "photo": filename  # Update photo field
    }

    db.students.update_one({"_id": ObjectId(student_id)}, {"$set": updated_data})
    
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


######################################################################################
#                     Adding Mark                                                     |
######################################################################################
@app.route('/search-marks/', methods=['GET', 'POST'])
def search_marks():
    if request.method == 'POST':
        reg_no = request.form.get('regNo')
        student = db.students.find_one({'regNo': reg_no})

        if student:
            return redirect(url_for('marks', st_class=student['class'], regNo=student['regNo']))
        else:
            return render_template('search_marks.html', error="No student found.")

    return render_template('search_marks.html')

@app.route('/marks/<st_class>/<regNo>/', methods=['GET', 'POST'])
def marks(st_class, regNo): 
    student = db.students.find_one({'regNo': regNo, 'class': st_class})  
    error = None
    success = None

    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        marks = request.form.get('marks', '').strip()

        if not subject or not marks:  
            error = "All fields are required."
        elif not marks.isdigit() or not (0 <= int(marks) <= 100):  
            error = "Marks must be between 0 and 100."
        else:
            existing_subjects = [mark['subject'].lower() for mark in student.get('marks', [])]
            if subject.lower() in existing_subjects:
                error = f"Marks for '{subject}' already exist."
            else:
                db.students.update_one(
                    {'regNo': regNo, 'class': st_class},  
                    {'$push': {'marks': {'subject': subject, 'marks': int(marks)}}}
                )
                student = db.students.find_one({'regNo': regNo, 'class': st_class})  
                success = f"Marks for '{subject}' added successfully!"

    return render_template('marks.html', student=student, error=error, success=success)



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

if __name__ == '__main__':
    app.run(debug=True)

