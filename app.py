import os
import uuid
from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret"

# ================= FILE UPLOAD CONFIG =================

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DATABASE CONFIG =================

database_url = os.environ.get("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ================= MODELS =================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Create tables AFTER model definition
with app.app_context():
    db.create_all()

# ================= SHARED LINKS =================

shared_links = {}

# ================= ROUTES =================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            return redirect(url_for("dashboard", username=username))

    return render_template("login.html")


@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    email = request.form["email"]
    password = generate_password_hash(request.form["password"])

    new_user = User(username=username, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()

    return redirect("/")


@app.route("/dashboard/<username>")
def dashboard(username):
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    os.makedirs(user_folder, exist_ok=True)

    files = os.listdir(user_folder)
    return render_template("dashboard.html", files=files, username=username)


@app.route("/upload/<username>", methods=["POST"])
def upload(username):
    file = request.files["file"]
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    os.makedirs(user_folder, exist_ok=True)

    file.save(os.path.join(user_folder, file.filename))

    return redirect(url_for("dashboard", username=username))


@app.route("/download/<username>/<filename>")
def download(username, filename):
    return send_from_directory(
        os.path.join(app.config['UPLOAD_FOLDER'], username),
        filename,
        as_attachment=True
    )


@app.route("/delete/<username>/<filename>")
def delete(username, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], username, filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    return redirect(url_for("dashboard", username=username))


@app.route("/preview/<username>/<filename>")
def preview(username, filename):
    return send_from_directory(
        os.path.join(app.config['UPLOAD_FOLDER'], username),
        filename
    )


# ================= SEARCH =================

@app.route("/search/<username>")
def search(username):
    query = request.args.get("q", "").lower()

    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    os.makedirs(user_folder, exist_ok=True)

    matched_files = [
        f for f in os.listdir(user_folder)
        if query in f.lower()
    ]

    return render_template("dashboard.html", files=matched_files, username=username)


# ================= SHARE =================

@app.route("/share/<username>/<filename>")
def share(username, filename):
    token = str(uuid.uuid4())
    shared_links[token] = (username, filename)

    return f"Share Link:<br>https://cloud-data-storage.onrender.com/shared/{token}"


@app.route("/shared/<token>")
def shared(token):
    if token in shared_links:
        username, filename = shared_links[token]
        return send_from_directory(
            os.path.join(app.config['UPLOAD_FOLDER'], username),
            filename,
            as_attachment=True
        )
    return "Invalid or expired link"


# ================= RUN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
