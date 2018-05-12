import os, sys
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    jsonify,
    make_response,
    g
)
from flask_compress import Compress
import sqlalchemy
from passlib.hash import sha256_crypt
import operator
import uuid

### CS50 wrapper for SQLAlchemy
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
server = Flask(__name__)
server.config["SEND_FILE_MAX_AGE_DEFAULT"] = 1  # disable caching

Compress(server)

server.secret_key = uuid.uuid4().hex

server.config['ALLOWED_EXTENSIONS'] = set(['png', 'PNG', 'jpg', 'JPG', 'jpeg', 'JPEG', 'ico', 'ICO'])

### File type confirmation
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in server.config['ALLOWED_EXTENSIONS']

### Convert string to int type possibility confirmation
def RepresentsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


### configure root directory path relative to this file
THIS_FOLDER_G = ""
if getattr(sys, 'frozen', False):
    # frozen
    THIS_FOLDER_G = os.path.dirname(sys.executable)
else:
    # unfrozen
    THIS_FOLDER_G = os.path.dirname(os.path.realpath(__file__))

### configure CS50 Library to use SQLite database
db = SQL("sqlite:///" + THIS_FOLDER_G + "/db/system.db")

### Disable cache
@server.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

### Store current session to global variable "g"
@server.before_request
def before_request():
    g.systemsettings = {}
    systemsettings = db.execute("SELECT * FROM systemsettings WHERE id=:id", id=1)
    g.systemsettings["institutionname"] = systemsettings[0]["institutionname"]
    g.systemsettings["icoURL"] = systemsettings[0]["icoURL"]
    g.systemsettings["pngURL"] = systemsettings[0]["pngURL"]
    g.systemsettings["jpgURL"] = systemsettings[0]["jpgURL"]
    g.systemsettings["nameinheader"] = systemsettings[0]["nameinheader"]
    g.systemsettings["logoinheader"] = systemsettings[0]["logoinheader"]

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


### check if app is running
@server.route("/check_if_app_is_running")
def check_if_app_is_running():
    return 'App Is Running ...'

### Root
@server.route("/")
def index():
    if g.user:
        return redirect(url_for("home"))
    else:
        return redirect(url_for("login"))

### Home
@server.route("/home")
def home():
    if g.user:
        numofstudents = len(db.execute("SELECT * FROM students WHERE status=:status", status="Active"))
        numofadmins = len(db.execute("SELECT * FROM admins"))
        return render_template("home.html", numofstudents=numofstudents, numofadmins=(numofadmins - 1))
    else:
        return redirect(url_for("login"))


'''
    Login/Logout
'''
### Login
@server.route("/login", methods=["GET", "POST"])
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
@server.route("/logout")
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
@server.route("/administrators")
def administrators():
    if g.user and g.role == "root":
        return render_template("administrators.html")
    else:
        return redirect(url_for("home"))

### Get admins data via ajax to show on main administrators page
@server.route("/getadmins", methods=["GET", "POST"])
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
@server.route("/saveadmininfo", methods=["GET", "POST"])
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
                    imgExt = db.execute("SELECT * FROM admins WHERE id=:id", id=int(id))
                    imgExt = imgExt[0]["imgURL"]
                    imgExt = imgExt.split(".")
                    imgExt = imgExt[-1]
                    try:
                        os.remove(os.path.join(THIS_FOLDER_G + "/static/img/db/admins/", "admin_" + id + "." + imgExt))
                    except:
                        pass
                    image.save(os.path.join(THIS_FOLDER_G + "/static/img/db/admins/", imagename))
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
@server.route("/addnewadmin", methods=["GET", "POST"])
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
                    image.save(os.path.join(THIS_FOLDER_G + "/static/img/db/admins/", imagename))
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
@server.route("/deleteadmin", methods=["GET", "POST"])
def deleteadmin():
    if g.user and g.role == "root":
        if request.method == "POST":
            id = request.values.get("id")

            admins = db.execute("SELECT * FROM admins")

            for i in range(len(admins)):
                if admins[i]["id"] == int(id):
                    firstname = admins[i]["firstname"]
                    lastname = admins[i]["lastname"]
                    imgExt = admins[i]["imgURL"]
                    imgExt = imgExt.split(".")
                    imgExt = imgExt[-1]
                    try:
                        os.remove(os.path.join(THIS_FOLDER_G + "/static/img/db/admins/", "admin_" + id + "." + imgExt))
                    except:
                        pass
                    db.execute("DELETE FROM admins WHERE id=:id", id=int(id))
                    return jsonify([{"status": "success", "msg": "Deleted", "firstname": firstname, "lastname": lastname}])
    else:
        return redirect(url_for("home"))


'''
    User profile of the currently logged in user(admin)
'''
### Show currently logged in user's profile
@server.route("/userprofile", methods=["GET", "POST"])
def userprofile():
    if g.user:
        return render_template("userprofile.html")
    else:
        return redirect(url_for("home"))

### Get currently logged in user's data via ajax to view on user profile
@server.route("/getuserprofile", methods=["GET", "POST"])
def getuserprofile():
    if g.user:
        user = db.execute("SELECT * FROM admins where id=:id", id=int(g.user))
        return jsonify(user)
    else:
        return redirect(url_for("home"))

### Save user profile changes via ajax
@server.route("/saveuserprofile", methods=["GET", "POST"])
def saveuserprofile():
    if g.user:
        if request.method == "POST":
            id = request.values.get("id")
            firstname = request.values.get("firstname")
            lastname = request.values.get("lastname")
            username = request.values.get("username")
            oldpassword = request.values.get("oldpassword")
            password = request.values.get("password")
            confirmpassword = request.values.get("confirmpassword")
            contact = request.values.get("contact")
            image = request.files["imgURL"]

            admins = db.execute("SELECT * FROM admins")

            for i in range(len(admins)):
                if admins[i]["username"] == username and admins[i]["id"] != int(id):
                    return jsonify([{"status": "error", "msg": "Username already taken."}])

            users = db.execute("SELECT * FROM admins WHERE id=:id", id=int(g.user))

            if password != "":
                if password != confirmpassword:
                    return jsonify([{"status": "error", "msg": "Confirm new password."}])

                if sha256_crypt.verify(oldpassword, users[0]["password"]) == True:
                    db.execute("UPDATE admins SET password=:password WHERE id=:id", password=sha256_crypt.hash(password), id=int(id))
                else:
                    return jsonify([{"status": "error", "msg": "Old password did not match."}])

            if image:
                if allowed_file(image.filename) == True:
                    imagename = image.filename
                    imageext = imagename.split(".")[-1]
                    imagename = "admin_" + str(id) + "." + imageext
                    imgExt = db.execute("SELECT * FROM admins WHERE id=:id", id=int(id))
                    imgExt = imgExt[0]["imgURL"]
                    imgExt = imgExt.split(".")
                    imgExt = imgExt[-1]
                    try:
                        os.remove(os.path.join(THIS_FOLDER_G + "/static/img/db/admins/", "admin_" + id + "." + imgExt))
                    except:
                        pass
                    image.save(os.path.join(THIS_FOLDER_G + "/static/img/db/admins/", imagename))
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
@server.route("/students")
def students():
    if g.user:
        students = db.execute("SELECT * FROM students WHERE status=:status", status="Active")
        students = sorted(students, key=lambda k: str.lower(k["firstname"]))
        return render_template("students.html", students=students)
    else:
        return redirect(url_for("home"))

### Main students page. View all currently inactive students
@server.route("/students/inactive")
def inactivestudents():
    if g.user:
        students = db.execute("SELECT * FROM students WHERE status=:status", status="Inactive")
        students = sorted(students, key=lambda k: str.lower(k["firstname"]))
        return render_template("students.html", students=students, inactive=True)
    else:
        return redirect(url_for("home"))

### View th profile of a specific student based on student ID
@server.route("/studentprofile/<id>")
def studentprofile(id):
    if g.user:
        student = db.execute("SELECT * FROM students WHERE id=:id", id=int(id))
        if len(student) > 0:
            if student[0]["status"] == "Inactive":
                return render_template("studentprofile.html", student=student[0], inactive=True)
            else:
                return render_template("studentprofile.html", student=student[0])
        else:
            return render_template("notfound.html", msg="Student Not Found.")
    else:
        return redirect(url_for("home"))

### Get student data via ajax to view on student profile based on student ID
@server.route("/getstudentprofile/<id>")
def getstudentprofile(id):
    if g.user:
        student = db.execute("SELECT * FROM students WHERE id=:id", id=int(id))
        if len(student) > 0:
            return jsonify(student)
        else:
            return render_template("notfound.html", msg="Student Not Found.")
    else:
        return redirect(url_for("home"))

### Save student data changes via ajax based on student ID
@server.route("/savestudentinfo/<id>", methods=["GET", "POST"])
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

            if status != "Active" and status != "Inactive":
                return jsonify([{"status": "error", "msg": "Invalid status."}])

            if image:
                if allowed_file(image.filename) == True:
                    imagename = image.filename
                    imageext = imagename.split(".")[-1]
                    imagename = "student_" + str(id) + "." + imageext
                    imgExt = db.execute("SELECT * FROM students WHERE id=:id", id=int(id))
                    imgExt = imgExt[0]["imgURL"]
                    imgExt = imgExt.split(".")
                    imgExt = imgExt[-1]
                    try:
                        os.remove(os.path.join(THIS_FOLDER_G + "/static/img/db/students/", "student_" + id + "." + imgExt))
                    except:
                        pass
                    image.save(os.path.join(THIS_FOLDER_G + "/static/img/db/students/", imagename))
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
@server.route("/addnewstudent", methods=["GET", "POST"])
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
                        image.save(os.path.join(THIS_FOLDER_G + "/static/img/db/students/", imagename))
                        imgURL = "../static/img/db/students/" + imagename
                        db.execute("UPDATE students SET imgURL=:imgURL WHERE id=:id", imgURL=imgURL, id=int(id))
                else:
                    return jsonify([{"status": "error", "msg": "File extension not supported."}])
            else:
                db.execute("INSERT INTO students (firstname, lastname, fathername, contact, gender, dob, address, class, admissiondate, monthlyfee, imgURL) VALUES (:firstname, :lastname, :fathername, :contact, :gender, :dob, :address, :class_, :admissiondate, :monthlyfee, :imgURL)", firstname=firstname, lastname=lastname, fathername=fathername, contact=contact, gender=gender, dob=dob, address=address, class_=class_, admissiondate=admissiondate, monthlyfee=int(monthlyfee), imgURL=imgURL)

            return jsonify([{"status": "success", "msg": "Changes saved."}])
    else:
        return redirect(url_for("home"))

### Delete student based on student ID
@server.route("/deletestudent/<id>", methods=["GET", "POST"])
def deletestudent(id):
    id = id
    students = db.execute("SELECT * FROM students WHERE id=:id", id=int(id))
    imgExt = students[0]["imgURL"]
    imgExt = imgExt.split(".")
    imgExt = imgExt[-1]
    try:
        os.remove(os.path.join(THIS_FOLDER_G + "/static/img/db/students/", "student_" + id + "." + imgExt))
    except:
        pass
    db.execute("DELETE FROM students WHERE id=:id", id=int(id))
    db.execute("DELETE FROM testrecords WHERE studentID=:studentID", studentID=int(id))
    db.execute("DELETE FROM feerecords WHERE studentID=:studentID", studentID=int(id))
    return redirect(url_for("students"))


'''
    Test Records
'''
### Main test records page
@server.route("/testrecords")
def testrecords():
    if g.user:
        records = db.execute("SELECT * FROM testrecords")
        return render_template("testrecords.html", records=records)
    else:
        return redirect(url_for("home"))

### View all test records page
@server.route("/alltestrecords")
def alltestrecords():
    if g.user:
        records = db.execute("SELECT * FROM testrecords")
        records.reverse()
        return render_template("alltestrecords.html", records=records)
    else:
        return redirect(url_for("home"))

### View test record of a specific student based on student ID
@server.route("/testrecord/<id>")
def fetchtestrecord(id):
    if g.user:
        records = db.execute("SELECT * FROM testrecords WHERE studentID=:id", id=int(id))
        if len(records) < 1:
            return render_template("notfound.html", msg="Record Not Found.")
        else:
            records.reverse()
            return render_template("studenttestrecord.html", records=records)
    else:
        return redirect(url_for("home"))

### Add test record of a specific student based on student ID
@server.route("/addtestrecords/<i>")
def addtestrecords(i):
    if g.user:
        return render_template("addtestrecords.html", i=int(i))
    else:
        return redirect(url_for("home"))

### Add new fee record according to student ID page
@server.route("/addstudenttestrecord/<id>")
def addstudenttestrecord(id):
    if g.user:
        return render_template("addtestrecords.html", i=1, id=id)
    else:
        return redirect(url_for("home"))

### Add new test records via ajax
@server.route("/addnewtestrecord", methods=["POST"])
def addnewtestrecord():
    if g.user:
        if request.method == "POST":
            studentID = request.values.get("studentID")
            date = request.values.get("date")
            subject = request.values.get("subject")
            description = request.values.get("description")
            totalmarks = request.values.get("totalmarks")
            obtainedmarks = request.values.get("obtainedmarks")
            remarks = request.values.get("remarks")

            if studentID == "" or date == "" or subject == "" or totalmarks == "" or obtainedmarks == "":
                return jsonify([{"status": "error", "msg": "Incomplete data."}])
            elif RepresentsInt(studentID) != True or RepresentsInt(totalmarks) != True or RepresentsInt(obtainedmarks) != True:
                return jsonify([{"status": "error", "msg": "Incompatible data."}])

            student = db.execute("SELECT * FROM students WHERE id=:id", id=int(studentID))
            if len(student) < 1:
                return jsonify([{"status": "error", "msg": "No Student with entered ID."}])


            db.execute("INSERT INTO testrecords (studentID, studentName, studentFrName, date, class, subject, description, totalmarks, obtainedmarks, obtainedpercentage, remarks) VALUES (:studentID, :studentName, :studentFrName, :date, :class_, :subject, :description, :totalmarks, :obtainedmarks, :obtainedpercentage, :remarks)", studentID=int(student[0]["id"]), studentName=str(student[0]["firstname"] + " " + student[0]["lastname"]), studentFrName=student[0]["fathername"], date=date, class_=student[0]["class"], subject=subject, description=description, totalmarks=int(totalmarks), obtainedmarks=int(obtainedmarks), obtainedpercentage=int(int(obtainedmarks)/int(totalmarks)*100), remarks=remarks)
            return jsonify([{"status": "success", "msg": "Changes saved."}])
    else:
        return redirect(url_for("home"))

### Edit test record
@server.route("/edittestrecord/<id>")
def edittestrecord(id):
    if g.user and g.role == "root":
        id = id
        record = db.execute("SELECT * FROM testrecords WHERE id=:id", id=int(id))
        if len(record) < 1:
            return render_template("notfound.html", msg="Record Not Found.")
        else:
            return render_template("edittestrecord.html", i=1, record=record[0])
    else:
        return redirect(url_for("home"))

### Update test record via ajax
@server.route("/updatetestrecord/<id>", methods=["POST"])
def updatetestrecord(id):
    if g.user and g.role == "root":
        if request.method == "POST":
            id = id
            studentID = request.values.get("studentID")
            studentName = request.values.get("studentName")
            studentFrName = request.values.get("studentFrName")
            date = request.values.get("date")
            class_ = request.values.get("class")
            subject = request.values.get("subject")
            description = request.values.get("description")
            totalmarks = request.values.get("totalmarks")
            obtainedmarks = request.values.get("obtainedmarks")
            remarks = request.values.get("remarks")

            if studentID == "" or studentName == "" or studentFrName == "" or date == "" or class_ == "" or subject == "" or totalmarks == "" or obtainedmarks == "":
                return jsonify([{"status": "error", "msg": "Incomplete data."}])
            elif RepresentsInt(studentID) != True or RepresentsInt(totalmarks) != True or RepresentsInt(obtainedmarks) != True:
                return jsonify([{"status": "error", "msg": "Incompatible data."}])

            student = db.execute("SELECT * FROM students WHERE id=:id", id=int(studentID))
            if len(student) < 1:
                return jsonify([{"status": "error", "msg": "No Student with entered ID."}])

            db.execute("UPDATE testrecords SET studentID=:studentID WHERE id=:id", studentID=studentID, id=int(id))
            db.execute("UPDATE testrecords SET studentName=:studentName WHERE id=:id", studentName=studentName, id=int(id))
            db.execute("UPDATE testrecords SET studentFrName=:studentFrName WHERE id=:id", studentFrName=studentFrName, id=int(id))
            db.execute("UPDATE testrecords SET date=:date WHERE id=:id", date=date, id=int(id))
            db.execute("UPDATE testrecords SET class=:class_ WHERE id=:id", class_=class_, id=int(id))
            db.execute("UPDATE testrecords SET subject=:subject WHERE id=:id", subject=subject, id=int(id))
            db.execute("UPDATE testrecords SET description=:description WHERE id=:id", description=description, id=int(id))
            db.execute("UPDATE testrecords SET totalmarks=:totalmarks WHERE id=:id", totalmarks=totalmarks, id=int(id))
            db.execute("UPDATE testrecords SET obtainedmarks=:obtainedmarks WHERE id=:id", obtainedmarks=obtainedmarks, id=int(id))
            db.execute("UPDATE testrecords SET obtainedpercentage=:obtainedpercentage WHERE id=:id", obtainedpercentage=int(int(obtainedmarks)/int(totalmarks)*100), id=int(id))
            db.execute("UPDATE testrecords SET remarks=:remarks WHERE id=:id", remarks=remarks, id=int(id))

            return jsonify([{"status": "success", "msg": "Changes saved."}])
    else:
        return redirect(url_for("home"))

### Delete test record based on record ID
@server.route("/deletetestrecord/<id>", methods=["GET", "POST"])
def deletetestrecord(id):
    id = id
    db.execute("DELETE FROM testrecords WHERE id=:id", id=int(id))
    return redirect(url_for("testrecords"))


'''
    Fee Records
'''
### Main fee records page
@server.route("/feerecords")
def feerecords():
    if g.user:
        records = db.execute("SELECT * FROM feerecords")
        return render_template("feerecords.html", records=records)
    else:
        return redirect(url_for("home"))

### View all fee records page
@server.route("/allfeerecords")
def allfeerecords():
    if g.user:
        records = db.execute("SELECT * FROM feerecords")
        records.reverse()
        return render_template("allfeerecords.html", records=records)
    else:
        return redirect(url_for("home"))

### View fee record of a specific student based on student ID
@server.route("/feerecord/<id>")
def fetchfeerecord(id):
    if g.user:
        records = db.execute("SELECT * FROM feerecords WHERE studentID=:id", id=int(id))
        if len(records) < 1:
            return render_template("notfound.html", msg="Record Not Found.")
        else:
            records.reverse()
            return render_template("studentfeerecord.html", records=records)
    else:
        return redirect(url_for("home"))

### Add fee record of a specific student based on student ID
@server.route("/addfeerecords/<i>")
def addfeerecords(i):
    if g.user:
        return render_template("addfeerecords.html", i=int(i))
    else:
        return redirect(url_for("home"))

### Add new fee record according to student ID page
@server.route("/addstudentfeerecord/<id>")
def addstudentfeerecord(id):
    if g.user:
        return render_template("addfeerecords.html", i=1, id=id)
    else:
        return redirect(url_for("home"))

### Add new fee records via ajax
@server.route("/addnewfeerecord", methods=["POST"])
def addnewfeerecord():
    if g.user:
        if request.method == "POST":
            studentID = request.values.get("studentID")
            date = request.values.get("date")
            feefor = request.values.get("feefor")
            depositedfee = request.values.get("depositedfee")

            if studentID == "" or date == "" or feefor == "" or depositedfee == "":
                return jsonify([{"status": "error", "msg": "Incomplete data."}])
            elif RepresentsInt(studentID) != True or RepresentsInt(depositedfee) != True:
                return jsonify([{"status": "error", "msg": "Incompatible data."}])

            student = db.execute("SELECT * FROM students WHERE id=:id", id=int(studentID))
            if len(student) < 1:
                return jsonify([{"status": "error", "msg": "No Student with entered ID."}])


            lastR_ID = db.execute("INSERT INTO feerecords (studentID, studentName, studentFrName, date, feefor, depositedfee) VALUES (:studentID, :studentName, :studentFrName, :date, :feefor, :depositedfee)", studentID=int(student[0]["id"]), studentName=str(student[0]["firstname"] + " " + student[0]["lastname"]), studentFrName=student[0]["fathername"], date=date, feefor=feefor, depositedfee=int(depositedfee))
            
            return jsonify([{"status": "success", "msg": "Changes saved.", "lastrowID": lastR_ID}])
    else:
        return redirect(url_for("home"))

### Download fee receipt
@server.route("/downloadfeereceipt/<id>")
def downloadfeereceipt(id):
    if g.user:
        id = id
        feeRecord = db.execute("SELECT * FROM feerecords WHERE id=:id", id=int(id))
        if len(feeRecord) < 1:
            return render_template("notfound.html", msg="Record Not Found.")
        else:
            return render_template("downloadfeereceipt.html", msg="Download will start in a moment ...", feeRecord=feeRecord[0])
    else:
        return redirect(url_for("home"))

### Edit fee record
@server.route("/editfeerecord/<id>")
def editfeerecord(id):
    if g.user and g.role == "root":
        id = id
        record = db.execute("SELECT * FROM feerecords WHERE id=:id", id=int(id))
        if len(record) < 1:
            return render_template("notfound.html", msg="Record Not Found.")
        else:
            return render_template("editfeerecord.html", i=1, record=record[0])
    else:
        return redirect(url_for("home"))

### Update fee record via ajax
@server.route("/updatefeerecord/<id>", methods=["POST"])
def updatefeerecord(id):
    if g.user and g.role == "root":
        if request.method == "POST":
            id = id
            studentID = request.values.get("studentID")
            studentName = request.values.get("studentName")
            studentFrName = request.values.get("studentFrName")
            date = request.values.get("date")
            feefor = request.values.get("feefor")
            depositedfee = request.values.get("depositedfee")

            if studentID == "" or studentName == "" or studentFrName == "" or date == "" or feefor == "" or depositedfee == "":
                return jsonify([{"status": "error", "msg": "Incomplete data."}])
            elif RepresentsInt(studentID) != True or RepresentsInt(depositedfee) != True:
                return jsonify([{"status": "error", "msg": "Incompatible data."}])

            student = db.execute("SELECT * FROM students WHERE id=:id", id=int(studentID))
            if len(student) < 1:
                return jsonify([{"status": "error", "msg": "No Student with entered ID."}])

            db.execute("UPDATE feerecords SET studentID=:studentID WHERE id=:id", studentID=studentID, id=int(id))
            db.execute("UPDATE feerecords SET studentName=:studentName WHERE id=:id", studentName=studentName, id=int(id))
            db.execute("UPDATE feerecords SET studentFrName=:studentFrName WHERE id=:id", studentFrName=studentFrName, id=int(id))
            db.execute("UPDATE feerecords SET date=:date WHERE id=:id", date=date, id=int(id))
            db.execute("UPDATE feerecords SET feefor=:feefor WHERE id=:id", feefor=feefor, id=int(id))
            db.execute("UPDATE feerecords SET depositedfee=:depositedfee WHERE id=:id", depositedfee=depositedfee, id=int(id))

            return jsonify([{"status": "success", "msg": "Changes saved."}])
    else:
        return redirect(url_for("home"))

### Delete fee record based on record ID
@server.route("/deletefeerecord/<id>", methods=["GET", "POST"])
def deletefeerecord(id):
    id = id
    db.execute("DELETE FROM feerecords WHERE id=:id", id=int(id))
    return redirect(url_for("feerecords"))


'''
    System Settings
'''
### System settings page
@server.route("/systemsettings")
def systemsettings():
    if g.user and g.role == "root":
        return render_template("systemsettings.html")
    else:
        return redirect(url_for("home"))

### Get system settings via ajax
@server.route("/getsystemsettings")
def getsystemsettings():
    if g.user and g.role == "root":
        systemsettings = db.execute("SELECT * FROM systemsettings where id=:id", id=1)
        return jsonify(systemsettings)
    else:
        return redirect(url_for("home"))

### Save system settings changes via ajax
@server.route("/savesystemsettings", methods=["GET", "POST"])
def savesystemsettings():
    if g.user and g.role == "root":
        if request.method == "POST":
            id = request.values.get("id")
            institutionname = request.values.get("institutionname")
            nameinheader = request.values.get("nameinheader")
            logoinheader = request.values.get("logoinheader")
            pngURL = request.files["pngURL"]
            jpgURL = request.files["jpgURL"]
            icoURL = request.files["icoURL"]

            print(institutionname, nameinheader, logoinheader)

            if institutionname == "":
                return jsonify([{"status": "error", "msg": "Institution Name is Mandatory"}])
            
            if (nameinheader != "true" and nameinheader != "false") or (logoinheader != "true" and logoinheader != "false"):
                return jsonify([{"status": "error", "msg": "Incompatible Values for true/false"}])

            if pngURL:
                if allowed_file(pngURL.filename) == True:
                    imagename = pngURL.filename
                    imageext = imagename.split(".")[-1]
                    imagename = "logo." + imageext
                    pngURL.save(os.path.join(THIS_FOLDER_G + "/static/img/system/", imagename))
                    pngURL = "../static/img/system/" + imagename
                    db.execute("UPDATE systemsettings SET pngURL=:pngURL WHERE id=:id", pngURL=pngURL, id=1)
                else:
                    return jsonify([{"status": "error", "msg": "File extension not supported."}])

            if jpgURL:
                if allowed_file(jpgURL.filename) == True:
                    imagename = jpgURL.filename
                    imageext = imagename.split(".")[-1]
                    imagename = "logo." + imageext
                    jpgURL.save(os.path.join(THIS_FOLDER_G + "/static/img/system/", imagename))
                    jpgURL = "../static/img/system/" + imagename
                    db.execute("UPDATE systemsettings SET jpgURL=:jpgURL WHERE id=:id", jpgURL=jpgURL, id=1)
                else:
                    return jsonify([{"status": "error", "msg": "File extension not supported."}])

            if icoURL:
                if allowed_file(icoURL.filename) == True:
                    imagename = icoURL.filename
                    imageext = imagename.split(".")[-1]
                    imagename = "logo." + imageext
                    icoURL.save(os.path.join(THIS_FOLDER_G + "/static/img/system/", imagename))
                    icoURL = "../static/img/system/" + imagename
                    db.execute("UPDATE systemsettings SET icoURL=:icoURL WHERE id=:id", icoURL=icoURL, id=1)
                else:
                    return jsonify([{"status": "error", "msg": "File extension not supported."}])

            db.execute("UPDATE systemsettings SET institutionname=:institutionname WHERE id=:id", institutionname=institutionname, id=1)
            db.execute("UPDATE systemsettings SET nameinheader=:nameinheader WHERE id=:id", nameinheader=nameinheader, id=1)
            db.execute("UPDATE systemsettings SET logoinheader=:logoinheader WHERE id=:id", logoinheader=logoinheader, id=1)

            return jsonify([{"status": "success", "msg": "Changes saved."}])
    else:
        return redirect(url_for("home"))


def run_server():
    server.run(host="127.0.0.1", port=5100, threaded=True)
    # server.run(debug=True)


if __name__ == "__main__":
    run_server()
