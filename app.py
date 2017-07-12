'''
    App: Student Record System
    Tech Stack: Python(Flask), SQLite, HTML, CSS, Javascript(JQuery)
    Author: Ahmed Noor
'''

### Imports
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify, g
from flask_compress import Compress
import sqlalchemy
from cs50 import SQL
from passlib.hash import sha256_crypt
import operator
import uuid
from werkzeug import secure_filename
import os

class SQL(object):
    """Wrap SQLAlchemy to provide a simple SQL API."""

    def __init__(self, url):
        """
        Create instance of sqlalchemy.engine.Engine.

        URL should be a string that indicates database dialect and connection arguments.

        http://docs.sqlalchemy.org/en/latest/core/engines.html#sqlalchemy.create_engine
        """
        try:
            self.engine = sqlalchemy.create_engine(url)
        except Exception as e:
            raise RuntimeError(e)

    def execute(self, text, *multiparams, **params):
        """
        Execute a SQL statement.
        """
        try:

            # bind parameters before statement reaches database, so that bound parameters appear in exceptions
            # http://docs.sqlalchemy.org/en/latest/core/sqlelement.html#sqlalchemy.sql.expression.text
            # https://groups.google.com/forum/#!topic/sqlalchemy/FfLwKT1yQlg
            # http://docs.sqlalchemy.org/en/latest/core/connections.html#sqlalchemy.engine.Engine.execute
            # http://docs.sqlalchemy.org/en/latest/faq/sqlexpressions.html#how-do-i-render-sql-expressions-as-strings-possibly-with-bound-parameters-inlined
            statement = sqlalchemy.text(text).bindparams(*multiparams, **params)
            result = self.engine.execute(str(statement.compile(compile_kwargs={"literal_binds": True})))

            # if SELECT (or INSERT with RETURNING), return result set as list of dict objects
            if result.returns_rows:
                rows = result.fetchall()
                return [dict(row) for row in rows]

            # if INSERT, return primary key value for a newly inserted row
            elif result.lastrowid is not None:
                return result.lastrowid

            # if DELETE or UPDATE (or INSERT without RETURNING), return number of rows matched
            else:
                return result.rowcount

        # if constraint violated, return None
        except sqlalchemy.exc.IntegrityError:
            return None

        # else raise error
        except Exception as e:
            raise RuntimeError(e)


### configure flask
app = Flask(__name__)
# Compress(app)

app.secret_key = uuid.uuid4().hex

app.config['ALLOWED_EXTENSIONS'] = set(['png', 'PNG', 'jpg', 'JPG', 'jpeg', 'JPEG'])

### File type confirmation
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

### Convert string to int type possibility confirmation
def RepresentsInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False


### configure CS50 Library to use SQLite database
db = SQL("sqlite:///./db/system.db")

### Disable cache
@app.after_request
#def add_header(r):
#    """
#    Add headers to both force latest IE rendering engine or Chrome Frame,
#    and also to cache the rendered page for 10 minutes.
#    """
#    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#    r.headers["Pragma"] = "no-cache"
#    r.headers["Expires"] = "0"
#    r.headers['Cache-Control'] = 'public, max-age=0'
#    return r

### Store current session to global variable "g"
@app.before_request
def before_request():
    g.user = None
    g.firstname = None
    g.lastname = None
    g.role = None
    g.logged_in = None
    if "user" in session:
        g.user = session["user"]
        g.username = session["username"]
        g.firstname = session["firstname"]
        g.lastname = session["lastname"]
        g.role = session["role"]
        g.logged_in = session["logged_in"]


### Root
@app.route("/")
def index():
    if g.user:
        return redirect(url_for("home"))
    else:
        return redirect(url_for("login"))

### Home
@app.route("/home")
def home():
    if g.user:
        numofstudents = len(db.execute("SELECT * FROM students WHERE status=:status", status="active"))
        numofadmins = len(db.execute("SELECT * FROM admins"))
        return render_template("home.html", numofstudents=numofstudents, numofadmins=(numofadmins - 1))
    else:
        return redirect(url_for("login"))


'''
    Login/Logout
'''
### Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = db.execute("SELECT * FROM admins WHERE username=:username", username=username)
        if len(users) > 0:
            if users[0]["username"] == username and sha256_crypt.verify(password, users[0]["password"]) == True:
                session.pop("user", None)
                session.pop("username", None)
                session.pop("firstname", None)
                session.pop("lastname", None)
                session.pop("role", None)
                session.pop("logged_in", None)
                session["user"] = str(users[0]["id"])
                session["username"] = users[0]["username"]
                session["firstname"] = users[0]["firstname"]
                session["lastname"] = users[0]["lastname"]
                session["role"] = users[0]["role"]
                session["logged_in"] = True
                return redirect(url_for("home"))
            else:
                return render_template("login.html", error="Invalid Username or Password.")
        else:
            return render_template("login.html", error="Invalid Username or Password.")

### Logout
@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("username", None)
    session.pop("firstname", None)
    session.pop("lastname", None)
    session.pop("role", None)
    session.pop("logged_in", None)
    return redirect(url_for("login"))


'''
    Administrators
'''
### Main administrators page
@app.route("/administrators")
def administrators():
    if g.user and g.role == "root":
        return render_template("administrators.html")
    else:
        return redirect(url_for("home"))

### Get admins data via ajax to show on main administrators page
@app.route("/getadmins", methods=["GET", "POST"])
def getadmins():
    if g.user and g.role == "root":
        admins = db.execute("SELECT * FROM admins")
        admins = sorted(admins, key=lambda k: str.lower(k["firstname"]))
        for i in range(len(admins)):
            if admins[i]["username"] == g.username:
                admins.pop(i)
                break
        return jsonify(admins)
    else:
        return redirect(url_for("home"))

### Save admin info via ajax
@app.route("/saveadmininfo", methods=["GET", "POST"])
def saveadmininfo():
    if g.user and g.role == "root":
        if request.method == "POST":
            id = request.values.get("id")
            firstname = request.values.get("firstname")
            lastname = request.values.get("lastname")
            username = request.values.get("username")
            password = request.values.get("password")
            contact = request.values.get("contact")
            role = request.values.get("role")
            image = request.files["imgURL"]

            admins = db.execute("SELECT * FROM admins")

            for i in range(len(admins)):
                if admins[i]["username"] == username and admins[i]["id"] != int(id):
                    return jsonify([{"status": "error", "msg": "Username already taken."}])
            
            if image:
                if allowed_file(image.filename) == True:
                    imagename = image.filename
                    imageext = imagename.split(".")[-1]
                    imagename = "admin_" + str(id) + "." + imageext
                    image.save(os.path.join(os.getcwd()+"/static/img/db/admins", imagename))
                    imgURL = "../static/img/db/admins/" + imagename
                    db.execute("UPDATE admins SET imgURL=:imgURL WHERE id=:id", imgURL=imgURL, id=int(id))
                else:
                    return jsonify([{"status": "error", "msg": "File extension not supported."}])

            db.execute("UPDATE admins SET firstname=:firstname WHERE id=:id", firstname=firstname, id=int(id))
            db.execute("UPDATE admins SET lastname=:lastname WHERE id=:id", lastname=lastname, id=int(id))
            db.execute("UPDATE admins SET username=:username WHERE id=:id", username=username, id=int(id))
            db.execute("UPDATE admins SET contact=:contact WHERE id=:id", contact=contact, id=int(id))
            db.execute("UPDATE admins SET role=:role WHERE id=:id", role=role, id=int(id))
            
            if password != "":
                db.execute("UPDATE admins SET password=:password WHERE id=:id", password=sha256_crypt.hash(password), id=int(id))

            return jsonify([{"status": "success", "msg": "Changes saved."}])
    else:
        return redirect(url_for("home"))

### Add admin info via ajax
@app.route("/addnewadmin", methods=["GET", "POST"])
def addnewadmin():
    if g.user and g.role == "root":
        if request.method == "POST":
            firstname = request.values.get("firstname")
            lastname = request.values.get("lastname")
            username = request.values.get("username")
            oldpassword = request.values.get("oldpassword")
            password = request.values.get("password")
            contact = request.values.get("contact")
            role = request.values.get("role")
            image = request.files["imgURL"]

            admins = db.execute("SELECT * FROM admins")

            if firstname == "" or lastname == "" or username == "" or password == "":
                return jsonify([{"status": "error", "msg": "Incomplete Details."}])

            for i in range(len(admins)):
                if admins[i]["username"] == username:
                    return jsonify([{"status": "error", "msg": "Username already taken."}])
            
            imgURL = "../static/img/system/default-prof-img.png"
            if image:
                if allowed_file(image.filename) == True:
                    db.execute("INSERT INTO admins (username, firstname, lastname, password, role, contact, imgURL) VALUES (:username, :firstname, :lastname, :password, :role, :contact, :imgURL)", username=username, firstname=firstname, lastname=lastname, password=sha256_crypt.hash(password), role=role, contact=contact, imgURL=imgURL)
                    newuser = db.execute("SELECT * FROM admins WHERE username=:username", username=username)

                    imagename = image.filename
                    imageext = imagename.split(".")[-1]
                    imagename = "admin_" + str(newuser[0]["id"]) + "." + imageext
                    image.save(os.path.join(os.getcwd()+"/static/img/db/admins", imagename))
                    imgURL = "../static/img/db/admins/" + imagename
                    db.execute("UPDATE admins SET imgURL=:imgURL WHERE id=:id", imgURL=imgURL, id=newuser[0]["id"])
                else:
                    return jsonify([{"status": "error", "msg": "File extension not supported."}])
            else:
                db.execute("INSERT INTO admins (username, firstname, lastname, password, role, contact, imgURL) VALUES (:username, :firstname, :lastname, :password, :role, :contact, :imgURL)", username=username, firstname=firstname, lastname=lastname, password=sha256_crypt.hash(password), role=role, contact=contact, imgURL=imgURL)
            
            return jsonify([{"status": "success", "msg": "Changes saved."}])
    else:
        return redirect(url_for("home"))

### Delete admin via ajax
@app.route("/deleteadmin", methods=["GET", "POST"])
def deleteadmin():
    if g.user and g.role == "root":
        if request.method == "POST":
            id = request.values.get("id")

            admins = db.execute("SELECT * FROM admins")

            for i in range(len(admins)):
                if admins[i]["id"] == int(id):
                    firstname = admins[i]["firstname"]
                    lastname = admins[i]["lastname"]
                    db.execute("DELETE FROM admins WHERE id=:id", id=int(id))
                    return jsonify([{"status": "success", "msg": "Deleted", "firstname": firstname, "lastname": lastname}])
    else:
        return redirect(url_for("home"))


'''
    User profile of the currently logged in user(admin)
'''
### Show currently logged in user's profile
@app.route("/userprofile", methods=["GET", "POST"])
def userprofile():
    if g.user:
        return render_template("userprofile.html")
    else:
        return redirect(url_for("home"))

### Get currently logged in user's data via ajax to view on user profile
@app.route("/getuserprofile", methods=["GET", "POST"])
def getuserprofile():
    if g.user:
        user = db.execute("SELECT * FROM admins where id=:id", id=int(g.user))
        return jsonify(user)
    else:
        return redirect(url_for("home"))

### Save user profile changes via ajax
@app.route("/saveuserprofile", methods=["GET", "POST"])
def saveuserprofile():
    if g.user:
        if request.method == "POST":
            id = request.values.get("id")
            firstname = request.values.get("firstname")
            lastname = request.values.get("lastname")
            username = request.values.get("username")
            oldpassword = request.values.get("oldpassword")
            password = request.values.get("password")
            contact = request.values.get("contact")
            image = request.files["imgURL"]

            admins = db.execute("SELECT * FROM admins")

            for i in range(len(admins)):
                if admins[i]["username"] == username and admins[i]["id"] != int(id):
                    return jsonify([{"status": "error", "msg": "Username already taken."}])
            
            users = db.execute("SELECT * FROM admins WHERE id=:id", id=int(g.user))
            
            if password != "":
                if sha256_crypt.verify(oldpassword, users[0]["password"]) == True:
                    db.execute("UPDATE admins SET password=:password WHERE id=:id", password=sha256_crypt.hash(password), id=int(id))
                else:
                    return jsonify([{"status": "error", "msg": "Password did not match."}])

            if image:
                if allowed_file(image.filename) == True:
                    imagename = image.filename
                    imageext = imagename.split(".")[-1]
                    imagename = "admin_" + str(id) + "." + imageext
                    image.save(os.path.join(os.getcwd()+"/static/img/db/admins", imagename))
                    imgURL = "../static/img/db/admins/" + imagename
                    db.execute("UPDATE admins SET imgURL=:imgURL WHERE id=:id", imgURL=imgURL, id=int(id))
                else:
                    return jsonify([{"status": "error", "msg": "File extension not supported."}])

            db.execute("UPDATE admins SET firstname=:firstname WHERE id=:id", firstname=firstname, id=int(id))
            db.execute("UPDATE admins SET lastname=:lastname WHERE id=:id", lastname=lastname, id=int(id))
            db.execute("UPDATE admins SET username=:username WHERE id=:id", username=username, id=int(id))
            db.execute("UPDATE admins SET contact=:contact WHERE id=:id", contact=contact, id=int(id))
            
            users = db.execute("SELECT * FROM admins WHERE id=:id", id=int(g.user))
            
            if len(users) > 0:
                session["username"] = users[0]["username"]
                session["firstname"] = users[0]["firstname"]
                session["lastname"] = users[0]["lastname"]
                session["role"] = users[0]["role"]

            return jsonify([{"status": "success", "msg": "Changes saved."}])
    else:
        return redirect(url_for("home"))


'''
    Students
'''
### Main students page. View all currently active students
@app.route("/students")
def students():
    if g.user:
        students = db.execute("SELECT * FROM students WHERE status=:status", status="active")
        students = sorted(students, key=lambda k: str.lower(k["firstname"]))
        return render_template("students.html", students=students)
    else:
        return redirect(url_for("home"))

### Main students page. View all currently inactive students
@app.route("/students/inactive")
def inactivestudents():
    if g.user:
        students = db.execute("SELECT * FROM students WHERE status=:status", status="inactive")
        students = sorted(students, key=lambda k: str.lower(k["firstname"]))
        return render_template("students.html", students=students, inactive=True)
    else:
        return redirect(url_for("home"))

### View th profile of a specific student based on student ID
@app.route("/studentprofile/<id>")
def studentprofile(id):
    if g.user:
        student = db.execute("SELECT * FROM students WHERE id=:id", id=int(id))
        if len(student) > 0:
            if student[0]["status"] == "inactive":
                return render_template("studentprofile.html", student=student[0], inactive=True)
            else:
                return render_template("studentprofile.html", student=student[0])
        else:
            return redirect(url_for("students"))
    else:
        return redirect(url_for("home"))

### Get student data via ajax to view on student profile based on student ID
@app.route("/getstudentprofile/<id>")
def getstudentprofile(id):
    if g.user:
        student = db.execute("SELECT * FROM students WHERE id=:id", id=int(id))
        if len(student) > 0:
            return jsonify(student)
        else:
            return redirect(url_for("students"))
    else:
        return redirect(url_for("home"))

### Save student data changes via ajax based on student ID
@app.route("/savestudentinfo/<id>", methods=["GET", "POST"])
def savestudentinfo(id):
    if g.user:
        if request.method == "POST":
            id = id
            firstname = request.values.get("firstname")
            lastname = request.values.get("lastname")
            fathername = request.values.get("fathername")
            contact = request.values.get("contact")
            gender = request.values.get("gender")
            dob = request.values.get("dob")
            address = request.values.get("address")
            class_ = request.values.get("class")
            admissiondate = request.values.get("admissiondate")
            monthlyfee = request.values.get("monthlyfee")
            status = request.values.get("status")
            image = request.files["imgURL"]

            student = db.execute("SELECT * FROM students WHERE id=:id", id=int(id))

            if firstname == "" or lastname == "" or fathername == "" or contact == "" or gender == "" or dob == "" or address == "" or class_ == "" or admissiondate == "" or monthlyfee == "" or status == "":
                return jsonify([{"status": "error", "msg": "Incomplete Details."}])

            if len(student) < 1:
                return jsonify([{"status": "error", "msg": "Student does not exist."}])

            if status != "active" and status != "inactive":
                return jsonify([{"status": "error", "msg": "Invalid status."}])

            if image:
                if allowed_file(image.filename) == True:
                    imagename = image.filename
                    imageext = imagename.split(".")[-1]
                    imagename = "student_" + str(id) + "." + imageext
                    image.save(os.path.join(os.getcwd()+"/static/img/db/students", imagename))
                    imgURL = "../static/img/db/students/" + imagename
                    db.execute("UPDATE students SET imgURL=:imgURL WHERE id=:id", imgURL=imgURL, id=int(id))
                else:
                    return jsonify([{"status": "error", "msg": "File extension not supported."}])

            db.execute("UPDATE students SET firstname=:firstname WHERE id=:id", firstname=firstname, id=int(id))
            db.execute("UPDATE students SET lastname=:lastname WHERE id=:id", lastname=lastname, id=int(id))
            db.execute("UPDATE students SET fathername=:fathername WHERE id=:id", fathername=fathername, id=int(id))
            db.execute("UPDATE students SET contact=:contact WHERE id=:id", contact=contact, id=int(id))
            db.execute("UPDATE students SET gender=:gender WHERE id=:id", gender=gender, id=int(id))
            db.execute("UPDATE students SET dob=:dob WHERE id=:id", dob=dob, id=int(id))
            db.execute("UPDATE students SET address=:address WHERE id=:id", address=address, id=int(id))
            db.execute("UPDATE students SET class=:class_ WHERE id=:id", class_=class_, id=int(id))
            db.execute("UPDATE students SET admissiondate=:admissiondate WHERE id=:id", admissiondate=admissiondate, id=int(id))
            db.execute("UPDATE students SET monthlyfee=:monthlyfee WHERE id=:id", monthlyfee=int(monthlyfee), id=int(id))
            db.execute("UPDATE students SET status=:status WHERE id=:id", status=status, id=int(id))

            student = db.execute("SELECT * FROM students WHERE id=:id", id=int(id))

            return jsonify([{"status": "success", "msg": "Changes saved."}])
    else:
        return redirect(url_for("home"))

### Add new student via ajax
@app.route("/addnewstudent", methods=["GET", "POST"])
def addnewstudent():
    if g.user:
        if request.method == "POST":
            firstname = request.values.get("firstname")
            lastname = request.values.get("lastname")
            fathername = request.values.get("fathername")
            contact = request.values.get("contact")
            gender = request.values.get("gender")
            dob = request.values.get("dob")
            address = request.values.get("address")
            class_ = request.values.get("class")
            admissiondate = request.values.get("admissiondate")
            monthlyfee = request.values.get("monthlyfee")
            image = request.files["imgURL"]

            students = db.execute("SELECT * FROM students")

            if firstname == "" or lastname == "" or fathername == "" or contact == "" or gender == "" or dob == "" or address == "" or class_ == "" or admissiondate == "" or monthlyfee == "":
                return jsonify([{"status": "error", "msg": "Incomplete Details."}])
            elif RepresentsInt(monthlyfee) != True:
                return jsonify([{"status": "error", "msg": "Incompatible Details."}])
            
            imgURL = "../static/img/system/default-prof-img.png"
            if image:
                if allowed_file(image.filename) == True:
                    db.execute("INSERT INTO students (firstname, lastname, fathername, contact, gender, dob, address, class, admissiondate, monthlyfee, imgURL) VALUES (:firstname, :lastname, :fathername, :contact, :gender, :dob, :address, :class_, :admissiondate, :monthlyfee, :imgURL)", firstname=firstname, lastname=lastname, fathername=fathername, contact=contact, gender=gender, dob=dob, address=address, class_=class_, admissiondate=admissiondate, monthlyfee=int(monthlyfee), imgURL=imgURL)

                    students_ = db.execute("SELECT * FROM students")
                    student = None
                    for i in range(len(students_)):
                        for j in range(len(students_)):
                            if students_[i]["id"] >= students_[j]["id"]:
                                student = students_[i]
                    
                    if student != None and student['firstname'] == firstname and student['lastname'] == lastname and student['fathername'] == fathername and student['gender'] == gender and student['dob'] == dob and student['address'] == address and student['class'] == class_ and student['admissiondate'] == admissiondate and student['monthlyfee'] == int(monthlyfee):
                        id = student['id']
                        imagename = image.filename
                        imageext = imagename.split(".")[-1]
                        imagename = "student_" + str(id) + "." + imageext
                        image.save(os.path.join(os.getcwd()+"/static/img/db/students", imagename))
                        imgURL = "../static/img/db/students/" + imagename
                        db.execute("UPDATE students SET imgURL=:imgURL WHERE id=:id", imgURL=imgURL, id=int(id))
                else:
                    return jsonify([{"status": "error", "msg": "File extension not supported."}])
            else:
                db.execute("INSERT INTO students (firstname, lastname, fathername, contact, gender, dob, address, class, admissiondate, monthlyfee, imgURL) VALUES (:firstname, :lastname, :fathername, :contact, :gender, :dob, :address, :class_, :admissiondate, :monthlyfee, :imgURL)", firstname=firstname, lastname=lastname, fathername=fathername, contact=contact, gender=gender, dob=dob, address=address, class_=class_, admissiondate=admissiondate, monthlyfee=int(monthlyfee), imgURL=imgURL)
            
            return jsonify([{"status": "success", "msg": "Changes saved."}])
    else:
        return redirect(url_for("home"))


'''
    Test Records
'''
### Main test records page
@app.route("/testrecords")
def testrecords():
    if g.user:
        records = db.execute("SELECT * FROM testrecords")
        return render_template("testrecords.html", records=records)
    else:
        return redirect(url_for("home"))

### View all test records page
@app.route("/alltestrecords")
def alltestrecords():
    if g.user:
        records = db.execute("SELECT * FROM testrecords")
        for record in records:
            id = int(record["studentID"])
            student = db.execute("SELECT * from STUDENTS WHERE id=:id", id=id)
            record["studentNAME"] = student[0]["firstname"] + " " + student[0]["lastname"]
        records.reverse()
        return render_template("alltestrecords.html", records=records)
    else:
        return redirect(url_for("home"))

### View test record of a specific student based on student ID
@app.route("/testrecord/<id>")
def fetchtestrecord(id):
    if g.user:
        records = db.execute("SELECT * FROM testrecords WHERE studentID=:id", id=int(id))
        student = db.execute("SELECT * FROM students WHERE id=:id", id=int(id))
        if len(student) < 1:
            return "Student Does Not EXIST!"
        else:
            records.reverse()
            return render_template("studenttestrecord.html", records=records, studentName=student[0]["firstname"] + " " + student[0]["lastname"], studentID = str(student[0]["id"]))
    else:
        return redirect(url_for("home"))

### Add test record of a specific student based on student ID
@app.route("/addtestrecords/<i>")
def addtestrecords(i):
    if g.user:
        return render_template("addtestrecords.html", i=int(i))
    else:
        return redirect(url_for("home"))

### Add new fee record according to student ID page
@app.route("/addstudenttestrecord/<id>")
def addstudenttestrecord(id):
    if g.user:
        return render_template("addtestrecords.html", i=1, id=id)
    else:
        return redirect(url_for("home"))

### Add new test records via ajax
@app.route("/addnewtestrecord", methods=["POST"])
def addnewtestrecord():
    if g.user:
        if request.method == "POST":
            studentID = request.values.get("studentID")
            date = request.values.get("date")
            class_ = request.values.get("class")
            subject = request.values.get("subject")
            description = request.values.get("description")
            totalmarks = request.values.get("totalmarks")
            obtainedmarks = request.values.get("obtainedmarks")
            remarks = request.values.get("remarks")

            if studentID == "" or date == "" or class_ == "" or subject == "" or totalmarks == "" or obtainedmarks == "":
                return jsonify([{"status": "error", "msg": "Incomplete data."}])
            elif RepresentsInt(studentID) != True or RepresentsInt(totalmarks) != True or RepresentsInt(obtainedmarks) != True:
                return jsonify([{"status": "error", "msg": "Incompatible data."}])
            
            student = db.execute("SELECT * FROM students WHERE id=:id", id=int(studentID))
            if len(student) < 1:
                return jsonify([{"status": "error", "msg": "No Student with entered ID."}])


            db.execute("INSERT INTO testrecords (studentID, date, class, subject, description, totalmarks, obtainedmarks, obtainedpercentage, remarks) VALUES (:studentID, :date, :class_, :subject, :description, :totalmarks, :obtainedmarks, :obtainedpercentage, :remarks)", studentID=int(studentID), date=date, class_=class_, subject=subject, description=description, totalmarks=int(totalmarks), obtainedmarks=int(obtainedmarks), obtainedpercentage=int(int(obtainedmarks)/int(totalmarks)*100), remarks=remarks)
            return jsonify([{"status": "success", "msg": "Changes saved."}])
    else:
        return redirect(url_for("home"))


'''
    Fee Records
'''
### Main fee records page
@app.route("/feerecords")
def feerecords():
    if g.user:
        records = db.execute("SELECT * FROM feerecords")
        return render_template("feerecords.html", records=records)
    else:
        return redirect(url_for("home"))

### View all fee records page
@app.route("/allfeerecords")
def allfeerecords():
    if g.user:
        records = db.execute("SELECT * FROM feerecords")
        for record in records:
            id = int(record["studentID"])
            student = db.execute("SELECT * from STUDENTS WHERE id=:id", id=id)
            record["studentNAME"] = student[0]["firstname"] + " " + student[0]["lastname"]
        records.reverse()
        return render_template("allfeerecords.html", records=records)
    else:
        return redirect(url_for("home"))

### View fee record of a specific student based on student ID
@app.route("/feerecord/<id>")
def fetchfeerecord(id):
    if g.user:
        records = db.execute("SELECT * FROM feerecords WHERE studentID=:id", id=int(id))
        student = db.execute("SELECT * FROM students WHERE id=:id", id=int(id))
        if len(student) < 1:
            return "Student Does Not EXIST!"
        else:
            records.reverse()
            return render_template("studentfeerecord.html", records=records, studentName=student[0]["firstname"] + " " + student[0]["lastname"], studentID = str(student[0]["id"]))
    else:
        return redirect(url_for("home"))

### Add fee record of a specific student based on student ID
@app.route("/addfeerecords/<i>")
def addfeerecords(i):
    if g.user:
        return render_template("addfeerecords.html", i=int(i))
    else:
        return redirect(url_for("home"))

### Add new fee record according to student ID page
@app.route("/addstudentfeerecord/<id>")
def addstudentfeerecord(id):
    if g.user:
        return render_template("addfeerecords.html", i=1, id=id)
    else:
        return redirect(url_for("home"))

### Add new fee records via ajax
@app.route("/addnewfeerecord", methods=["POST"])
def addnewfeerecord():
    if g.user:
        if request.method == "POST":
            studentID = request.values.get("studentID")
            date = request.values.get("date")
            feemonth = request.values.get("feemonth")
            depositedfee = request.values.get("depositedfee")

            if studentID == "" or date == "" or feemonth == "" or depositedfee == "":
                return jsonify([{"status": "error", "msg": "Incomplete data."}])
            elif RepresentsInt(studentID) != True or RepresentsInt(depositedfee) != True:         
                return jsonify([{"status": "error", "msg": "Incompatible data."}])
            
            student = db.execute("SELECT * FROM students WHERE id=:id", id=int(studentID))
            if len(student) < 1:
                return jsonify([{"status": "error", "msg": "No Student with entered ID."}])


            db.execute("INSERT INTO feerecords (studentID, date, feemonth, depositedfee) VALUES (:studentID, :date, :feemonth, :depositedfee)", studentID=int(studentID), date=date, feemonth=feemonth, depositedfee=int(depositedfee))
            return jsonify([{"status": "success", "msg": "Changes saved."}])
    else:
        return redirect(url_for("home"))


### Run Flask App
if __name__ == "__main__":
    app.run(debug=True)
