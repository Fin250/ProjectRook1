from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}

# Utility function to check allowed file extensions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

# Routes
@app.route("/")
def home():
    gigs = [
        {"date": "2023-11-01", "venue": "The Underground", "city": "New York"},
        {"date": "2023-11-15", "venue": "Rock Arena", "city": "Los Angeles"},
        {"date": "2023-12-05", "venue": "Metal Hall", "city": "Chicago"},
    ]
    return render_template("home.html", gigs=gigs)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        gig_date = request.form.get("date")
        gig_venue = request.form.get("venue")
        gig_city = request.form.get("city")
        if gig_date and gig_venue and gig_city:
            flash("Gig added successfully!", "success")
        else:
            flash("All fields are required!", "danger")
    return render_template("admin.html")

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

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/past_events")
def past_events():
    return render_template("past_events.html")

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