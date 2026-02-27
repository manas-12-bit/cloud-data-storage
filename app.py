import os
import uuid
from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash



import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)
app.secret_key = "secret"



# ================= CLOUDINARY CONFIG =================

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
)

# ================= DATABASE CONFIG =================

database_url = os.environ.get("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODELS =================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    owner = db.Column(db.String(100), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    public_id = db.Column(db.String(300), nullable=False)
    is_private = db.Column(db.Boolean, default=True)

with app.app_context():
    db.create_all()

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

    if User.query.filter_by(username=username).first():
        return "Username already exists"

    new_user = User(username=username, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()

    return redirect("/")


@app.route("/dashboard/<username>")
def dashboard(username):
    files = File.query.filter_by(owner=username).all()
    return render_template("dashboard.html", files=files, username=username)


# ================= UPLOAD TO CLOUDINARY =================

@app.route("/upload/<username>", methods=["POST"])
def upload(username):
    file = request.files["file"]

    if not file:
        return redirect(url_for("dashboard", username=username))

    result = cloudinary.uploader.upload(
    file,
    folder=username,
    resource_type="auto"
)

    new_file = File(
        filename=file.filename,
        owner=username,
        file_url=result["secure_url"],
        public_id=result["public_id"],
        is_private=True
    )

    db.session.add(new_file)
    db.session.commit()

    return redirect(url_for("dashboard", username=username))


# ================= DOWNLOAD =================

@app.route("/download/<int:file_id>")
def download(file_id):
    file = File.query.get(file_id)
    return redirect(file.file_url)


# ================= DELETE =================

@app.route("/delete/<int:file_id>/<username>")
def delete(file_id, username):
    file = File.query.get(file_id)

    if file:
        cloudinary.uploader.destroy(file.public_id)
        db.session.delete(file)
        db.session.commit()

    return redirect(url_for("dashboard", username=username))


# ================= RENAME =================

@app.route("/rename/<int:file_id>/<username>", methods=["POST"])
def rename_file(file_id, username):
    new_name = request.form["new_name"]
    file = File.query.get(file_id)

    if file:
        file.filename = new_name
        db.session.commit()

    return redirect(url_for("dashboard", username=username))


# ================= TOGGLE PRIVATE =================

@app.route("/toggle/<int:file_id>/<username>")
def toggle_privacy(file_id, username):
    file = File.query.get(file_id)

    if file:
        file.is_private = not file.is_private
        db.session.commit()

    return redirect(url_for("dashboard", username=username))


# ================= SHARE =================

@app.route("/share/<int:file_id>")
def share(file_id):
    file = File.query.get(file_id)

    if file and not file.is_private:
        return f"Share Link:<br>{file.file_url}"

    return "File is private"

@app.route("/search/<username>")
def search(username):
    query = request.args.get("q", "")

    files = File.query.filter(
        File.owner == username,
        File.filename.ilike(f"%{query}%")
    ).all()

    return render_template("dashboard.html", files=files, username=username)


if __name__ == "__main__":
    app.run(debug=True)

