import os
import uuid
from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret"

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

shared_links = {}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username=request.form["username"]
        password=request.form["password"]

        user=User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password,password):
            return redirect(url_for("dashboard",username=username))
    return render_template("login.html")

@app.route("/register",methods=["POST"])
def register():
    u=request.form["username"]
    e=request.form["email"]
    p=generate_password_hash(request.form["password"])
    db.session.add(User(username=u,email=e,password=p))
    db.session.commit()
    return redirect("/")

@app.route("/dashboard/<username>")
def dashboard(username):
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)

    os.makedirs(user_folder, exist_ok=True)

    files = os.listdir(user_folder) if os.path.exists(user_folder) else []

    return render_template("dashboard.html", files=files, username=username)


@app.route("/upload/<username>",methods=["POST"])
def upload(username):
    f=request.files["file"]
    user_folder=os.path.join(UPLOAD_FOLDER,username)
    f.save(os.path.join(user_folder,f.filename))
    return redirect(url_for("dashboard",username=username))

@app.route("/download/<username>/<filename>")
def download(username,filename):
    return send_from_directory(os.path.join(UPLOAD_FOLDER,username),filename,as_attachment=True)

@app.route("/delete/<username>/<filename>")
def delete(username,filename):
    os.remove(os.path.join(UPLOAD_FOLDER,username,filename))
    return redirect(url_for("dashboard",username=username))

@app.route("/preview/<username>/<filename>")
def preview(username, filename):
    return send_from_directory(os.path.join(UPLOAD_FOLDER, username), filename)

# ================= SEARCH ROUTE =================

@app.route("/search/<username>")
def search(username):
    query = request.args.get("q", "").lower()

    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    os.makedirs(user_folder, exist_ok=True)

    files = []
    if os.path.exists(user_folder):
        for f in os.listdir(user_folder):
            if query in f.lower():
                files.append(f)

    return render_template("dashboard.html", files=files, username=username)


# ================= SHARE =================

@app.route("/share/<username>/<filename>")
def share(username,filename):
    token=str(uuid.uuid4())
    shared_links[token]=(username,filename)
    return f"Share Link:<br>http://127.0.0.1:5000/shared/{token}"

@app.route("/shared/<token>")
def shared(token):
    u,f=shared_links[token]
    return send_from_directory(os.path.join(UPLOAD_FOLDER,u),f,as_attachment=True)

# ================= RUN =================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)

