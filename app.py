from flask import Flask, render_template, request, url_for, redirect
from pymongo import MongoClient
from config import DB_URL  # Import DB_URL from config.py
from bson import ObjectId

client = MongoClient(DB_URL)  # Create database connection
db = client['students']  # Create database object

app = Flask(__name__)


@app.route('/')
def index():
    student_list = db.students.find({})
    return render_template('index.html', student_list=student_list)


@app.route('/add-student/', methods=['POST'])
def addStudent():
    name = request.form['name']
    regNo = request.form['registerNumber']
    st_class = request.form['class']
    email = request.form['email']
    phone = request.form['phone']

    db.students.insert_one({
        'name': name,
        'regNo': regNo,
        'class': st_class,
        'email': email,
        'phone': phone
    })

    return redirect(url_for('index'))


@app.route('/delete-student/<id>/')
def deleteStudent(id):
    db.students.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('index'))


@app.route('/update-student/<id>/',methods=['GET','POST'])
def editStudent(id):
    if request.method == 'GET':
        student = db.students.find_one({'_id': ObjectId(id)})
        students = db.students.find({})
        return render_template('index.html', student = student, student_list = students)
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

@app.route('/login/',methods=['GET','POST'])
def user_login():
    return render_template('user_login.html')

@app.route('/register/',methods=['GET','POST'])
def user_register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        name_of_college = request.form['college']
        place = request.form['place']
        country = request.form['country']

        user = {
            email: email,
            password: password,
            phone: phone,
            name_of_college: name_of_college,
            place:place,
            country: country
        }

        db.users.insert_one(user)
        return redirect(url_for('user_login'))

    return render_template('user_register.html')

if __name__ == '__main__':
    app.run(debug=True)
