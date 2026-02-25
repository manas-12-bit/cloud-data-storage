import os
import uuid
from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret"

# ================= FILE UPLOAD CONFIG =================

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DATABASE CONFIG =================

database_url = os.environ.get("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

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
    is_private = db.Column(db.Boolean, default=True)


# 🔥 Create tables (Flask 3 compatible)
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


@app.route("/upload/<username>", methods=["POST"])
def upload(username):
    file = request.files["file"]

    if not file:
        return redirect(url_for("dashboard", username=username))

    user_folder = os.path.join(app.config["UPLOAD_FOLDER"], username)
    os.makedirs(user_folder, exist_ok=True)

    file_path = os.path.join(user_folder, file.filename)
    file.save(file_path)

    new_file = File(filename=file.filename, owner=username, is_private=True)
    db.session.add(new_file)
    db.session.commit()

    return redirect(url_for("dashboard", username=username))


@app.route("/download/<username>/<filename>")
def download(username, filename):
    return send_from_directory(
        os.path.join(app.config["UPLOAD_FOLDER"], username),
        filename,
        as_attachment=True,
    )


@app.route("/delete/<username>/<filename>")
def delete(username, filename):
    file_record = File.query.filter_by(owner=username, filename=filename).first()

    if file_record:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], username, filename)

        if os.path.exists(file_path):
            os.remove(file_path)

        db.session.delete(file_record)
        db.session.commit()

    return redirect(url_for("dashboard", username=username))


@app.route("/preview/<username>/<filename>")
def preview(username, filename):
    return send_from_directory(
        os.path.join(app.config["UPLOAD_FOLDER"], username),
        filename,
    )


@app.route("/rename/<username>/<int:file_id>", methods=["POST"])
def rename_file(username, file_id):
    new_name = request.form["new_name"]

    file_record = File.query.get(file_id)

    if not file_record:
        return redirect(url_for("dashboard", username=username))

    old_path = os.path.join(app.config["UPLOAD_FOLDER"], username, file_record.filename)
    new_path = os.path.join(app.config["UPLOAD_FOLDER"], username, new_name)

    if os.path.exists(old_path):
        os.rename(old_path, new_path)

    file_record.filename = new_name
    db.session.commit()

    return redirect(url_for("dashboard", username=username))


@app.route("/toggle/<username>/<int:file_id>")
def toggle_privacy(username, file_id):
    file_record = File.query.get(file_id)

    if file_record:
        file_record.is_private = not file_record.is_private
        db.session.commit()

    return redirect(url_for("dashboard", username=username))


@app.route("/search/<username>")
def search(username):
    query = request.args.get("q", "")

    files = File.query.filter(
        File.owner == username,
        File.filename.ilike(f"%{query}%"),
    ).all()

    return render_template("dashboard.html", files=files, username=username)


@app.route("/share/<username>/<filename>")
def share(username, filename):
    file_record = File.query.filter_by(owner=username, filename=filename).first()

    if file_record and not file_record.is_private:
        token = str(uuid.uuid4())
        shared_links[token] = (username, filename)
        return f"Share Link:<br>https://cloud-data-storage.onrender.com/shared/{token}"

    return "File is private"


@app.route("/shared/<token>")
def shared(token):
    if token in shared_links:
        username, filename = shared_links[token]
        return send_from_directory(
            os.path.join(app.config["UPLOAD_FOLDER"], username),
            filename,
            as_attachment=True,
        )

    return "Invalid or expired link"


# ================= RUN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)