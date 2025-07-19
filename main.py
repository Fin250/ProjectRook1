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
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta
import os
import requests
import uuid
from collections import defaultdict
from time import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallbacksecret")
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])

users_raw = os.environ.get("ADMIN_USERS", "")
users = {}
for pair in users_raw.split(","):
    if ":" in pair:
        username, password = pair.split(":", 1)
        users[username] = bcrypt.generate_password_hash(password).decode("utf-8")

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
    __table_args__ = (db.UniqueConstraint("title", "date", "time", name="_event_uc"),)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

def format_date_with_ordinal(date):
    day = date.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return date.strftime(f"{day}{suffix} %B %Y")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("You must login to access this page", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
CHANNEL_ID = "UCDvFWE_kn242G_JzyuC_StA"

def get_recent_videos():
    url = (
        "https://www.googleapis.com/youtube/v3/search"
        "?key={key}&channelId={channel}&part=snippet,id&order=date&maxResults=10"
    ).format(key=YOUTUBE_API_KEY, channel=CHANNEL_ID)

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    videos = []
    for item in data.get("items", []):
        if item["id"]["kind"] == "youtube#video":
            videos.append({
                "id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"]
            })
    return videos

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

@app.route("/admin")
@login_required
def admin():
    events = Event.query.order_by(Event.date.asc(), Event.time.asc()).all()
    for event in events:
        event.formatted_date = format_date_with_ordinal(event.date)
    return render_template("admin.html", events=events)

@app.route("/admin/add-event", methods=["GET", "POST"])
@login_required
def add_event():
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

        if date < datetime.today().date():
            flash("Event date must be in the future", "danger")
            return redirect(request.url)

        existing = Event.query.filter_by(title=title, date=date, time=time).first()
        if existing:
            flash("An event with the same title, date, and time already exists.", "danger")
            return redirect(request.url)

        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
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

    return render_template("add_event.html")

@app.route("/admin/delete/<int:event_id>", methods=["POST"])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return "", 204

@app.route("/admin/edit/<int:event_id>", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)

    if request.method == "POST":
        event.title = request.form.get("title")
        date_str = request.form.get("date")
        time_str = request.form.get("time")

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            time = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            flash("Invalid date or time format", "danger")
            return redirect(request.url)

        if date < datetime.today().date():
            flash("Cannot set event date in the past", "danger")
            return redirect(request.url)

        event.date = date
        event.time = time
        event.bands = request.form.get("bands")
        event.description = request.form.get("description")
        event.ticket_link = request.form.get("ticket_link")

        file = request.files.get("image")
        if file and allowed_file(file.filename):
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
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
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            flash("File uploaded successfully!", "success")
            return redirect(url_for("upload"))
    return render_template("upload.html")

failed_logins = defaultdict(list)
MAX_ATTEMPTS = 10
WINDOW_SECONDS = 60

@app.route("/login", methods=["GET", "POST"])
def login():
    ip = get_remote_address()

    now = time()
    failed_attempts = failed_logins[ip]
    failed_attempts = [t for t in failed_attempts if now - t < WINDOW_SECONDS]
    failed_logins[ip] = failed_attempts

    if len(failed_attempts) >= MAX_ATTEMPTS:
        flash("Too many attempts, try again in a minute", "danger")
        return render_template("login.html")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        username_lookup = next((u for u in users if u.lower() == username.lower()), None)

        if username_lookup and bcrypt.check_password_hash(users[username_lookup], password):
            session["user"] = username_lookup
            failed_logins[ip] = []
            return redirect(url_for("admin"))
        else:
            failed_logins[ip].append(now)
            flash("Invalid username or password", "danger")
            return redirect(request.url)

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully!", "success")
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

@app.route("/venue")
def venue():
    return render_template("venue.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/podcast")
def podcast():
    recent_videos = get_recent_videos()
    latest_video_id = recent_videos[0]["id"] if recent_videos else None

    podcast_url_file = "podcast_url.txt"
    podcast_url = ""
    if os.path.exists(podcast_url_file):
        with open(podcast_url_file, "r") as f:
            podcast_url = f.read().strip()

    return render_template(
        "podcast.html",
        latest_video_id=latest_video_id,
        recent_videos=recent_videos,
        youtube_channel_id=CHANNEL_ID,
        podcast_url=podcast_url,
    )

@app.route("/event/<event_id_title>")
def event_detail(event_id_title):
    try:
        event_id = int(event_id_title.split("-", 1)[0])
    except (ValueError, IndexError):
        return render_template("404.html"), 404

    event = Event.query.get_or_404(event_id)
    return render_template("event.html", event=event)

@app.route("/admin/update-podcast", methods=["GET", "POST"])
@login_required
def update_podcast():
    podcast_url_file = "podcast_url.txt"
    current_url = ""
    if os.path.exists(podcast_url_file):
        with open(podcast_url_file, "r") as f:
            current_url = f.read().strip()

    if request.method == "POST":
        new_url = request.form.get("youtube_url", "").strip()
        if new_url:
            with open(podcast_url_file, "w") as f:
                f.write(new_url)
            flash("Podcast link updated!", "success")
            return redirect(url_for("update_podcast"))
        else:
            flash("Please enter a valid YouTube URL.", "danger")

    return render_template("update_podcast.html", current_url=current_url)

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

if __name__ == "__main__":
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])
    app.run(debug=True, port=5000)