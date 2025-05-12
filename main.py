from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    bands = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(200), nullable=False)
    ticket_link = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Utility function to check allowed file extensions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

def format_date_with_ordinal(date):
    day = date.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return date.strftime(f"{day}{suffix} %B %Y")

# Predefined admin users
users = {
    "totpresents": bcrypt.generate_password_hash("totpresents").decode("utf-8"),
    "hammerdown": bcrypt.generate_password_hash("hammerdown").decode("utf-8"),
    "fin": bcrypt.generate_password_hash("fin").decode("utf-8"),
}

# Routes
@app.route("/")
def home():
    current_time = datetime.now()
    events = Event.query.filter(
        (Event.date > current_time.date()) |
        ((Event.date == current_time.date()) & (Event.time >= (current_time - timedelta(hours=1)).time()))
    ).order_by(Event.date.asc(), Event.time.asc()).all()

    for event in events:
        event.formatted_date = format_date_with_ordinal(event.date)

    return render_template("home.html", events=events)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        title = request.form.get("title")
        date_str = request.form.get("date")
        time_str = request.form.get("time")
        bands = request.form.get("bands")
        description = request.form.get("description")
        ticket_link = request.form.get("ticket_link")

        file = request.files.get("image")

        if not (title and date_str and time_str and file and allowed_file(file.filename)):
            flash("Missing required fields or invalid image", "danger")
            return redirect(request.url)

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            time = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            flash("Invalid date or time format", "danger")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        image_url = f"uploads/{filename}"

        new_event = Event(
            title=title,
            date=date,
            time=time,
            bands=bands,
            description=description,
            ticket_link=ticket_link,
            image_url=image_url
        )

        db.session.add(new_event)
        db.session.commit()
        flash("Event added successfully!", "success")
        return redirect(url_for("admin"))

    # Query the database for events and pass them to the template
    events = Event.query.order_by(Event.date.asc(), Event.time.asc()).all()
    for event in events:
        event.formatted_date = format_date_with_ordinal(event.date)

    return render_template("admin.html", events=events)

@app.route("/admin/delete/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    if "user" not in session:
        return "Unauthorized", 401

    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return "", 204  # No content, used by JS to remove the card

@app.route("/admin/edit/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    if "user" not in session:
        return redirect(url_for("login"))

    event = Event.query.get_or_404(event_id)

    if request.method == "POST":
        event.title = request.form.get("title")
        event.date = datetime.strptime(request.form.get("date"), "%Y-%m-%d").date()
        time_str = request.form.get("time")
        try:
            event.time = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            event.time = datetime.strptime(time_str, "%H:%M:%S").time()

        event.bands = request.form.get("bands")
        event.description = request.form.get("description")
        event.ticket_link = request.form.get("ticket_link")

        file = request.files.get("image")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            event.image_url = f"uploads/{filename}"

        db.session.commit()
        flash("Event updated successfully!", "success")
        return redirect(url_for("admin"))

    return render_template("edit_event.html", event=event)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part", "danger")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("No selected file", "danger")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            flash("File uploaded successfully!", "success")
            return redirect(url_for("upload"))
    return render_template("upload.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in users and bcrypt.check_password_hash(users[username], password):
            session["user"] = username
            flash("Login successful!", "success")
            return redirect(url_for("admin"))
        else:
            flash("Invalid username or password", "danger")
            return redirect(request.url)

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully!", "success")
    return redirect(url_for("login"))

@app.before_request
def restrict_admin_page():
    if request.endpoint == "admin" and "user" not in session:
        flash("You must log in to access the admin page", "danger")
        return redirect(url_for("login"))

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/past_events")
def past_events():
    current_time = datetime.now()
    past_events = Event.query.filter(
        (Event.date < current_time.date()) |
        ((Event.date == current_time.date()) & (Event.time < (current_time - timedelta(hours=1)).time()))
    ).order_by(Event.date.desc(), Event.time.desc()).all()

    for event in past_events:
        event.formatted_date = format_date_with_ordinal(event.date)

    return render_template("past_events.html", events=past_events)

@app.route("/accessibility")
def accessibility():
    return render_template("accessibility.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

# Run app
if __name__ == "__main__":
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])
    app.run(debug=True, port=5000)