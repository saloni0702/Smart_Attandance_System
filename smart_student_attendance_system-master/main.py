from flask import Flask, render_template, request, session, redirect, url_for, Response
import json
from flask.helpers import flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from flask_mysqldb import MySQL
import MySQLdb.cursors
from mysql import connector
import mysql.connector
import csv
import cv2
from face_recognition_code import recognition
from sqlalchemy.exc import SQLAlchemyError
import datetime
import requests
#local files locations stored in config.json file
with open('config.json', 'r') as c:
    params = json.load(c)["params"]
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/test'
app.secret_key = 'super secret key'
app.config['upload_folder_student'] = params['upload_location_student']
app.config['upload_folder_faculty'] = params['upload_location_faculty']
app.config['upload_folder_student_data'] = params['upload_location_student_data']

db = SQLAlchemy(app)

#provide your database details here
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'test'

mydb = mysql.connector.connect(host='localhost', user='root', password='', database='test')

# Intialize MySQL
mysql = MySQL(app)

#global varibles
global present
present = []
global subname
subname=''
global subcode
subcode=''


#defining the classes for our database tables
class Test_faculty(db.Model):
    f_id = db.Column(db.String(11), nullable=False, primary_key=True)
    f_name = db.Column(db.String(11), nullable=False)
    f_password = db.Column(db.String(11), nullable=False)
    f_branch = db.Column(db.String(11), nullable=False)
    f_sem = db.Column(db.Integer, nullable=False)
    f_contact = db.Column(db.String(11), nullable=False)
    classes = db.relationship('Test_class', backref='test_faculty', lazy=True)
class Test_subject(db.Model):
    sub_branch = db.Column(db.String(11), nullable=False)
    sub_sem = db.Column(db.Integer, nullable=False)
    sub_code = db.Column(db.String(11), nullable=False, primary_key=True)
    sub_name = db.Column(db.String(11), nullable=False)
    subjects = db.relationship('Test_class', backref='test_subject', lazy=True)
class Test_student_class(db.Model):
    stu_id=db.Column(db.Integer,primary_key=True,nullable=False,autoincrement=True)
    s_id = db.Column(db.String(11),nullable=False)
    class_id = db.Column(db.Integer,nullable=False)
class Test_student(db.Model):
    s_id = db.Column(db.String(11), primary_key=True, nullable=False)
    s_name = db.Column(db.String(11), nullable=False)
    s_branch = db.Column(db.String(11), nullable=False)
    s_sem = db.Column(db.Integer, nullable=False)
    s_password = db.Column(db.String(11), nullable=False)
    s_contact = db.Column(db.Integer, nullable=False)
class Test_class(db.Model):
    class_id = db.Column(db.Integer, nullable=False, primary_key=True)
    class_sem = db.Column(db.Integer, nullable=False, primary_key=True)
    class_branch = db.Column(db.String(11), nullable=False, primary_key=True)
    f_id = db.Column(db.Integer, db.ForeignKey('test_faculty.f_id'), nullable=False)
    sub_code = db.Column(db.String(11), db.ForeignKey('test_subject.sub_code'), nullable=False)
class Test_attendance(db.Model):
    a_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    s_id = db.Column(db.String(11), nullable=False)
    a_present= db.Column(db.Boolean, nullable=False)
    sub_code= db.Column(db.String(11), nullable=False)
    a_date = db.Column(db.Date, nullable=False)

#homepage url
@app.route("/")
def home():
    session.clear()
    return render_template('index.html')

#loading page after providing credentials
@app.route("/admin", methods=['GET', 'POST'])
def signin():
    #admin authentication
    if ('user' in session and session['user'] == params['admin_name']):
        return render_template('admin.html')
    if request.method == 'POST':
        uname = request.form.get('uid')
        upass = request.form.get('pass')
        if (uname == params['admin_name'] and upass == params['admin_pass']):
            session['user'] = uname
            return render_template('admin.html')
    #faculty authentication
    if request.method == 'POST' and 'uid' in request.form and 'pass' in request.form:
        global id
        id = request.form['uid']
        password = request.form['pass']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM test_faculty WHERE f_id = %s AND f_password = %s', (id, password))
        fac_res = cursor.fetchone()
        if fac_res:
            session['loggedin'] = True
            session['id'] = fac_res['f_id']
            return render_template('faculty.html')
        else:
            msg = 'Incorrect username/password!'
    #student authentication
    if request.method == 'POST' and 'uid' in request.form and 'pass' in request.form:
        global stuid
        stuid = request.form['uid']
        password = request.form['pass']

        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM test_student WHERE s_id = %s AND s_password = %s', (id, password))
        # Fetch one record and return result
        stu_res = cursor.fetchone()
        # If account exists in accounts table in out database
        if stu_res:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['stuid'] = stu_res['s_id']
            # session['username'] = account['username']
            # Redirect to home page

            return render_template('student.html')
           # return 'Logged in successfully!'
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'

    return render_template('index.html')


#facultyform url for adding faculties in database
@app.route("/storefacultydetails", methods=['GET', 'POST'])
def storefacultydetails():
    if request.method == "POST":
        fid = request.form.get('fid')
        fname = request.form.get('fname')
        fpassword = request.form.get('fpassword1')
        fbranch = request.form.get('fbranch')
        fsem = request.form.get('fsemester')
        fcontact = request.form.get('fcontact')
        f = request.files['fimage']
        f.save(os.path.join(app.config['upload_folder_faculty'], secure_filename(f.filename)))
        entry_fac = Test_faculty(f_id=fid, f_name=fname, f_password=fpassword, f_branch=fbranch, f_sem=fsem,
                                 f_contact=fcontact)
        db.session.add(entry_fac)
        try:
            db.session.commit()
        except connector.DataError as err:
            flash("Data is improper")
        except SQLAlchemyError as err:
            db.session.rollback()
            err_msg = err.args[0]
            if "UNIQUE constraint failed: test_faculty.f_id" in err_msg:
                flash("error,  username already exists (%s)" % fid)
                return redirect(url_for('admin'))
            elif "FOREIGN KEY constraint failed" in err_msg:
                flash( "faculty does not exist")
                return render_template('admin.html')
            else:
                flash("unknown error adding user")
                return render_template('admin.html')
        #db.session.commit()
    return render_template('admin.html')


#url for adding subjects in database
@app.route("/addsubject", methods=['GET', 'POST'])
def addsubject():
    if request.method == "POST":
        sub_branch = request.form.get('sbranch')
        sub_sem = request.form.get('ssemester')
        sub_code = request.form.get('subcode')
        sub_name = request.form.get('subjectname')
        entry_sub = Test_subject(sub_code=sub_code, sub_name=sub_name, sub_branch=sub_branch, sub_sem=sub_sem)
        db.session.add(entry_sub)
        try:
            db.session.commit()
        except mysql.connector.DataError as err:
            flash("Data is improper")
        except mysql.connector.IntegrityError as err:
            db.session.rollback()
            err_msg = err.args[0]
            if "UNIQUE constraint failed: test_subject.subcode" in err_msg:
                flash("error, subjects sub_code already exists (%s)" % sub_code)
                return False
            elif "FOREIGN KEY constraint failed" in err_msg:
                flash( "Foriegn key error ..such data does not exist")
                return False
            else:
                flash("unknown error adding user")
                return False
        #db.session.commit()
    return render_template('subjectform.html')

#subjectpage
@app.route("/assignfacultysubject", methods=['GET', 'POST'])
def facultysubjects():
    return render_template('assignfacultysubject.html')



@app.route("/sub", methods=['GET', 'POST'])
def sub():
    if request.method == "POST":
        f_id = request.form.get('fid')
        session['faculty'] = f_id
    return redirect(url_for('subjectlist', f_id=f_id))


#subjectlist for particular f_id entered for creating class
@app.route("/subjectlist/<string:f_id>", methods=['GET', 'POST'])
def subjectlist(f_id):
    cursor1 = mysql.connection.cursor()
    cursor2 = mysql.connection.cursor()
    cursor3 = mysql.connection.cursor()
    query1 = "SELECT f_sem from test_faculty where f_id=%s"
    param1 = (f_id,)
    cursor1.execute(query1, param1)
    global sem
    sem=[x[0] for x in cursor1.fetchall()]
    query2 = "select f_branch from test_faculty where f_id=%s"
    param2 = (f_id,)
    cursor2.execute(query2, param2)
    global branch
    branch = [x[0] for x in cursor2.fetchall()]

    query3 = "SELECT sub_code from test_subject where sub_sem=%s and sub_branch=%s"
    param3 = (sem,branch,)
    cursor3.execute(query3, param3)
    subjectlist=[x[0] for x in cursor3.fetchall()]
    return render_template('subjectlist.html',sublist=subjectlist)

#storing the data into test_class
@app.route("/storeclass", methods=['GET', 'POST'])
def storeclass():
    if request.method=="POST":
        sub_code=request.form.get('selectsubject')
        entry_class = Test_class(class_sem=sem[0],class_branch=branch[0],f_id=session['faculty'],sub_code=sub_code)
        db.session.add(entry_class)
        try:
            db.session.commit()
            session.pop('faculty', None)
            session.pop('sem', None)
            session.pop('branch', None)
        except mysql.connector.DataError as err:
            flash("Data is improper")
        except mysql.connector.IntegrityError as err:
            db.session.rollback()
            err_msg = err.args[0]
            if "FOREIGN KEY constraint failed" in err_msg:
                flash("Foriegn key error...such data does not exist")
                return False

    return render_template('subjectlist.html')


@app.route("/studentform")
def studentdetails():
    return render_template('studentform.html')


#add the data of students from csv in database
@app.route("/nextpage", methods=['GET', 'POST'])
def nextpage():
    if request.method == "POST":
        stu_data_csv = request.files['scsv']
        stu_data_csv.save(
            os.path.join(app.config['upload_folder_student_data'], secure_filename(stu_data_csv.filename)))
        cursor = mydb.cursor()
        csv_data = csv.reader(
            open('C:\\Users\\ketul\\PycharmProjects\\SDP-project\\Database\\StudentData\\StudentData.csv'))
        next(csv_data)
        for row in csv_data:
            cursor.execute(
                'INSERT INTO test_student (s_id,s_name,s_password,s_branch,s_sem,s_contact) VALUES (%s,%s,%s,%s,%s,%s)',
                row)
        #mydb.commit()
        try:
            mydb.commit()
        except mysql.connector.DataError as err:
            flash("Data is improper")
        except mysql.connector.IntegrityError as err:
            db.session.rollback()
            err_msg = err.args[0]
            if  "UNIQUE constraint failed: test_student.s_id" in err_msg:
                flash("Enter other student_id. The entered s_id is already exist")
                return False
            elif "FOREIGN KEY constraint failed" in err_msg:
                flash("class or student does not exist")
                return False
            else:
                flash("unknown error adding user")
                return False
        cursor.close()
        cursor1 = mysql.connection.cursor()
        param1=()
        query1="SELECT test_student.s_id , test_class.class_id FROM test_student,test_class WHERE test_student.s_sem=test_class.class_sem AND test_student.s_branch=test_class.class_branch"
        l=cursor1.execute(query1,param1)
        print(l)
        for i in range(l):
            data=cursor1.fetchone()
            print(data)
            entry_fac = Test_student_class(s_id=data[0],class_id=data[1])
            db.session.add(entry_fac)
            db.session.commit()
    return render_template('addstudents.html')


#displaying facultyform
@app.route("/facultyform")
def facultydetails():
    return render_template('FacultyForm.html')

#displaying addstudent.html
@app.route("/assignstudentclass")
def assignstudentclass():
    return render_template('addstudents.html')


#displaying subjectform
@app.route("/subjectform")
def subjectdetails():
    return render_template('subjectform.html')

#taking attendance
@app.route("/attendance")
def attendance():
    return redirect(url_for('takeattendance', f_id=id))

#url for attedance for partucular faculty
@app.route("/takeattendance/<string:f_id>", methods=['GET', 'POST'])
def takeattendance(f_id):

    cursor = mysql.connection.cursor()
    data = cursor.execute(
        "select sub_name from test_subject as sub INNER JOIN test_class as cla on sub.sub_code=cla.sub_code where cla.f_id= %s",
        [f_id])

    return render_template('takeattendance.html', subject0=[x[0] for x in cursor.fetchall()], fid=f_id)

#page for adding new student photo in images folder
@app.route("/addnewstudentphoto")
def addnewstudentphoto():
    return render_template('addstudentphoto.html')

#display faculty.html
@app.route("/faculty")
def faculty():
    return render_template('faculty.html')

#adding student photoes in the images folder
@app.route("/studentphoto", methods=['GET', 'POST'])
def studentphoto():
    global stu_id
    stu_id = request.form.get('sid')
    return redirect(url_for('addstudentphoto', stuid=stu_id))

#using harcascade fetching face from image
@app.route("/addstudentphoto/<string:stuid>")
def addstudentphoto(stuid):
    cam = cv2.VideoCapture(0)

    face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

    count = 0
    while (True):
        ret, img = cam.read()
        faces = face_detector.detectMultiScale(img, 1.3, 5)
        for (x, y, w, h) in faces:
            x1 = x
            y1 = y
            x2 = x + w
            y2 = y + h
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 2)
            count += 1
            cv2.imwrite("images/" + stuid + ".jpg", img[y1:y2, x1:x2])
            cv2.imshow('image', img)
        k = cv2.waitKey(200) & 0xff
        if k == 27:
            break
        elif count >= 1:
            break
    cam.release()
    cv2.destroyAllWindows()
    return render_template('addstudentphoto.html')


#strating attendance
@app.route('/startattendance', methods=['GET', 'POST'])
def startattendance():

    try:
        if request.method=="POST" and 'selectsubject' in request.form :
            global subcode
            subcode = request.form['selectsubject']
    finally:
        pass




        return render_template('takeattendance.html')

#closing attendance and stroing data in csv file
@app.route('/closeattendance',methods=['GET','POST'])
def closeattendance():
    global subcode
    subcode=0


    return render_template('faculty.html')



#showing attendance for student page
@app.route("/showattendance", methods=['GET', 'POST'])
def showattendance():
    cursor1 = mysql.connection.cursor()
    cursor2 = mysql.connection.cursor()
    cursor3 = mysql.connection.cursor()
    cursor4 = mysql.connection.cursor()
    cursor5=mysql.connection.cursor()
    query1 = "SELECT s_name from test_student where s_id=%s"
    param1 = (stuid,)
    cursor1.execute(query1, param1)
    query2 = "select sub_code from test_class as cla inner join test_student_class as stu on cla.class_id=stu.class_id where s_id=%s"
    param2 = (stuid,)
    data1 = cursor2.execute(query2, param2)
    query3 = "SELECT count(s_id),sub_code from test_attendance where s_id=%s and a_present=1 group by sub_code"
    param3 = (stuid,)
    cursor3.execute(query3, param3)
    query5 = "SELECT count(s_id),sub_code from test_attendance where s_id=%s group by sub_code"
    param5 = (stuid,)
    cursor5.execute(query5, param5)
    query4 = "SELECT count(s_id) from test_attendance where s_id=%s"
    param4 = (stuid,)
    cursor4.execute(query4, param4)
    total=[x[0] for x in cursor4.fetchall()]
    attendancedetails = [x[0] for x in cursor3.fetchall()]
    subjectwise_total=[x[0] for x in cursor5.fetchall()]


    return render_template('showattendance.html', studentid=stuid, l=data1,attendancedetails = attendancedetails,
                           subjectdetails=[x[0] for x in cursor2.fetchall()],
                           studentname=[x[0] for x in cursor1.fetchall()],total=total,subjectwise_total=subjectwise_total)

#rendering the uploadattendance page
@app.route("/uploadattendance", methods=['GET', 'POST'])
def uploadattendance():
    return render_template('uploadattendance.html')

#saving attendance from csv file to the database
@app.route("/saveattendance",methods=['GET', 'POST'])
def saveattendance():
    if request.method=="POST":
        att_data_csv = request.files['acsv']
        att_data_csv.save(
            os.path.join(app.config['upload_folder_student_data'], secure_filename(att_data_csv.filename)))
        cursor = mysql.connection.cursor()
        with open('C:\\Users\\ketul\\PycharmProjects\\SDP-project\\my_csv.csv') as f:
            csv_data = csv.reader(f, delimiter=',', quotechar='"')
            for row in csv_data:
                if row:
                    query1 = "select sub_code from test_subject where sub_name=%s"
                    param1 = (row[2],)
                    cursor.execute(query1, param1)
                    sub_code = [x[0] for x in cursor.fetchall()]
                    print(sub_code)
                    entry_att = Test_attendance(s_id=row[0], a_present=int(row[1]), sub_code=sub_code, a_date=row[3])
                    db.session.add(entry_att)
                    db.session.commit()
    return render_template('uploadattendance.html')




@app.route('/recordattendance',methods=['GET','POST'])
def recordattendance():
    print(subcode)
    active=0
    if subcode!=0:
        active=1
    else:
        active=0
    return render_template('recordattendance.html',f_id=id,sub_code=subcode,active=active)

@app.route('/storeattendance',methods=['GET','POST'])
def storeattendance():
    input_embedding = recognition.create_input_image_embeddings()
    name, faces = recognition.recognize_faces_in_cam(input_embedding)
    print(name)
    print(faces)
    success=0
    if name!=0:
        success=1
    else:
        success=0
    return render_template('saveattendance.html',success=success)

app.run(debug=True)