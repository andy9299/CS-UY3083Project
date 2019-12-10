from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")
SALT = "cs3083"
query3_1a = "SELECT photoID, photoPoster FROM photo WHERE"


connection = pymysql.connect(host="localhost",
                             user="root",
                             password="",
                             db="finsta",
                             charset="utf8mb4",
                             port=3306,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")

@app.route("/home")
@login_required
def home():
    return render_template("home.html", username=session["username"])

@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")

@app.route("/images", methods=["GET"])
@login_required
def images():
    query = 'SELECT p.filepath, p.photoID, p.photoPoster ' \
            'FROM photo as p ' \
            'JOIN follow as f ON (f.username_followed = p.photoPoster) ' \
            'WHERE followstatus = TRUE AND allFollowers = TRUE AND username_follower = "' \
            + session["username"] \
            + '" UNION ' \
            'SELECT p.filepath, p.photoID, p.photoPoster ' \
            'FROM photo as p ' \
            'JOIN sharedwith as s ON (p.photoID = s.photoID) ' \
            'JOIN belongto as b ON (b.groupName = s.groupName AND b.owner_username = s.groupOwner) ' \
            'WHERE b.member_username = "' \
            + session["username"] +"\"" + \
            " ORDER BY photoID DESC"
    with connection.cursor() as cursor:
        cursor.execute(query)
        data = cursor.fetchall()
    return render_template("images.html", images=data)

@app.route("/image_info", methods=["GET", "POST"])
def image_info():
    query = 'SELECT p.filepath, p.photoID, p.photoPoster, per.firstName, per.lastName, p.postingdate ' \
            'FROM photo as p ' \
            'JOIN follow as f ON (f.username_followed = p.photoPoster) ' \
            'JOIN person as per ON (per.username = p.photoPoster) ' \
            'WHERE followstatus = TRUE AND allFollowers = TRUE AND username_follower = "' \
            + session["username"] \
            + '" AND p.photoID = "' \
            + request.form["photoID"] \
            + '" UNION ' \
            'SELECT p.filepath, p.photoID, p.photoPoster, per.firstName, per.lastName, p.postingdate ' \
            'FROM photo as p ' \
            'JOIN sharedwith as s ON (p.photoID = s.photoID) ' \
            'JOIN belongto as b ON (b.groupName = s.groupName AND b.owner_username = s.groupOwner) ' \
            'JOIN person as per ON (per.username = p.photoPoster) ' \
            'WHERE b.member_username = "' \
            + session["username"] +"\" " \
            'AND p.photoID = "' \
            + request.form["photoID"] + "\""
    #THIS QUERY IS MESSED UP WILL BE FIXED
    query2 = 'SELECT t.username, p1.firstName, p1.lastName ' \
             'FROM tagged as t ' \
             'JOIN person as p1 ON (t.username = p1.username) ' \
             'WHERE photoID IN ( ' \
             'SELECT photoID ' \
             'FROM photo JOIN follow ON (username_followed = photoPoster) ' \
             'WHERE followstatus = TRUE AND allFollowers = TRUE AND username_follower = "' \
             + session["username"] + "\"" + \
             ' UNION ' \
             'SELECT p.photoID ' \
             'FROM photo as p ' \
             'JOIN sharedwith as s ON (p.photoID = s.photoID) ' \
             'JOIN belongto as b ON (b.groupName = s.groupName AND b.owner_username = s.groupOwner) ' \
             'WHERE b.member_username = "' \
             + session["username"] + "\")" + \
             ' AND t.tagstatus = TRUE'
    with connection.cursor() as cursor:
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.execute(query2)
        data2 = cursor.fetchall()
    return render_template("image_info.html", image=data, tagged=data2)

@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")

@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")

@app.route("/loginAuth", methods=["GET", "POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"] + SALT
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)

@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]+SALT
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]
        bio = requestData["bio"]
        
        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO person (username, password, firstName, lastName, bio) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName, bio))
                #connection.commit()
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)    

        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)

@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")

@app.route("/uploadImage", methods=["GET", "POST"])
@login_required
def upload_image():
    if request.files:
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        allfollowers = request.form["AllFollowers"]
        caption = request.form["caption"]
        posting_time = time.strftime("%Y-%m-%d %H:%M:%S")
        username = session["username"]

        
        query = "INSERT INTO photo (postingdate, filepath, allFollowers, caption, photoPoster) VALUES (%s, %s, %s, %s, %s)"
        print(posting_time, filepath, allfollowers, caption)
        with connection.cursor() as cursor:
            cursor.execute(query, (posting_time, filepath, allfollowers, caption, username))
        message = "Image has been successfully uploaded."
        return render_template("upload.html", message=message)
    else:
        message = "Failed to upload image."
        return render_template("upload.html", message=message)

@app.route("/addLike", methods=["GET", "POST"])
def addLike():
    username = session['username']
    rating = request.form['rating']
    return render_template("likes.html")
    if request.form:
        queryPID = 'SELECT photoID ' \
            'FROM photo ' \
            'JOIN follow ON (username_followed = photoPoster) ' \
            'WHERE followstatus = TRUE AND allFollowers = TRUE AND username_follower = "' \
            + session["username"] \
            + '" UNION ' \
            'SELECT p.photoID ' \
            'FROM photo as p ' \
            'JOIN sharedwith as s ON (p.photoID = s.photoID) ' \
            'JOIN belongto as b ON (b.groupName = s.groupName AND b.owner_username = s.groupOwner) ' \
            'WHERE b.member_username = "' \
            + session["username"] +"\"" + \
            " ORDER BY photoID DESC"
        with connection.cursor() as cursor:
            cursor.execute(query) #finds photoIDs
        tstampsec = time.time()
        timestamp = time.ctime(tstampsec)
        query1 = 'INSERT INTO likes' \
                 'VALUES(' + username + photoID + timestamp + rating + ')'
        with connection.cursor() as cursor:
            cursor.execute(query1) #inserts values into the table
        return render_template("image_info.html", likes=likes)
    
    
#NEEDS TO BE UPDATED
@app.route("/imageSearch", methods=["GET", "POST"])
def imageSearch():
    if request.form:
        requestData = request.form
        poster = requestData["poster"]
        query = 'SELECT photoID ' \
                'FROM photo ' \
                'JOIN follow ON (username_followed = photoPoster) ' \
                'WHERE followstatus = TRUE AND allFollowers = TRUE AND username_follower = "' \
                + session["username"] + "\"" \
                + " AND photoPoster = \"" \
                + poster + "\"" \
                + ' UNION ' \
                'SELECT p.photoID ' \
                'FROM photo as p ' \
                'JOIN sharedwith as s ON (p.photoID = s.photoID) ' \
                'JOIN belongto as b ON (b.groupName = s.groupName AND b.owner_username = s.groupOwner) ' \
                'WHERE b.member_username = "' \
                + session["username"] + "\"" \
                + " AND p.photoPoster = \"" \
                + poster + "\""\
                + " ORDER BY photoID DESC"
        with connection.cursor() as cursor:
            cursor.execute(query)
        data = cursor.fetchall()
        return render_template("images_by_poster.html", poster=poster, images=data)
if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()
