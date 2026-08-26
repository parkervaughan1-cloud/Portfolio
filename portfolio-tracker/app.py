import os
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_from_directory, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-before-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{BASE_DIR / 'portfolio.db'}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

db = SQLAlchemy(app)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
ALLOWED_DOC_EXTENSIONS = {"pdf", "txt", "md", "doc", "docx"}

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    summary = db.Column(db.String(320), nullable=False)
    description = db.Column(db.Text, nullable=False)
    technologies = db.Column(db.String(500), default="")
    github_url = db.Column(db.String(500), default="")
    live_url = db.Column(db.String(500), default="")
    image_filename = db.Column(db.String(500), default="")
    document_filename = db.Column(db.String(500), default="")
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hero_eyebrow = db.Column(db.String(160), default="CYBERSECURITY • SOFTWARE • SYSTEMS")
    hero_title = db.Column(db.String(300), default="I build things, break things, and document what I learn.")
    hero_text = db.Column(db.Text, default="I'm Parker Vaughan. This portfolio tracks my cybersecurity, software development, homelab, infrastructure, and research projects in one place.")
    about_eyebrow = db.Column(db.String(160), default="ABOUT")
    about_title = db.Column(db.String(300), default="Hands-on learning, documented.")
    about_paragraph_one = db.Column(db.Text, default="I’m a cybersecurity student interested in defensive security, networking, systems, software development, and practical infrastructure.")
    about_paragraph_two = db.Column(db.Text, default="This site is also a project itself: it is designed to run in Docker on a Raspberry Pi and be published securely through Cloudflare Tunnel.")


def get_site_settings():
    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings()
        db.session.add(settings)
        db.session.commit()
    return settings

def slugify(value: str) -> str:
    value = value.lower().strip()
    cleaned = []
    last_dash = False
    for ch in value:
        if ch.isalnum():
            cleaned.append(ch)
            last_dash = False
        elif not last_dash:
            cleaned.append("-")
            last_dash = True
    slug = "".join(cleaned).strip("-")
    return slug or "project"

def unique_slug(title: str, project_id=None) -> str:
    base = slugify(title)
    slug = base
    i = 2
    while True:
        query = Project.query.filter_by(slug=slug)
        if project_id is not None:
            query = query.filter(Project.id != project_id)
        if not query.first():
            return slug
        slug = f"{base}-{i}"
        i += 1

def allowed_file(filename, allowed):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

def admin_logged_in():
    return bool(session.get("admin"))

def admin_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not admin_logged_in():
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped

@app.route("/")
def index():
    projects = Project.query.order_by(Project.featured.desc(), Project.created_at.desc()).all()
    settings = get_site_settings()
    return render_template("index.html", projects=projects, settings=settings)

@app.route("/projects/<slug>")
def project_detail(slug):
    project = Project.query.filter_by(slug=slug).first_or_404()
    tech = [t.strip() for t in project.technologies.split(",") if t.strip()]
    return render_template("project.html", project=project, tech=tech)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if admin_logged_in():
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        password = request.form.get("password", "")
        configured_hash = os.environ.get("ADMIN_PASSWORD_HASH")
        configured_password = os.environ.get("ADMIN_PASSWORD")

        valid = False
        if configured_hash:
            valid = check_password_hash(configured_hash, password)
        elif configured_password:
            valid = password == configured_password

        if valid:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Invalid password.", "error")

    return render_template("login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template("admin.html", projects=projects)

@app.route("/admin/projects/new", methods=["GET", "POST"])
@admin_required
def new_project():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        summary = request.form.get("summary", "").strip()
        description = request.form.get("description", "").strip()

        if not title or not summary or not description:
            flash("Title, summary, and description are required.", "error")
            return render_template("project_form.html", project=None)

        image_name = ""
        doc_name = ""

        image = request.files.get("image")
        if image and image.filename:
            if not allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
                flash("Unsupported image format.", "error")
                return render_template("project_form.html", project=None)
            image_name = f"{datetime.utcnow().timestamp()}-{secure_filename(image.filename)}"
            image.save(UPLOAD_DIR / image_name)

        document = request.files.get("document")
        if document and document.filename:
            if not allowed_file(document.filename, ALLOWED_DOC_EXTENSIONS):
                flash("Unsupported document format.", "error")
                return render_template("project_form.html", project=None)
            doc_name = f"{datetime.utcnow().timestamp()}-{secure_filename(document.filename)}"
            document.save(UPLOAD_DIR / doc_name)

        project = Project(
            title=title,
            slug=unique_slug(title),
            summary=summary,
            description=description,
            technologies=request.form.get("technologies", "").strip(),
            github_url=request.form.get("github_url", "").strip(),
            live_url=request.form.get("live_url", "").strip(),
            image_filename=image_name,
            document_filename=doc_name,
            featured=bool(request.form.get("featured")),
        )
        db.session.add(project)
        db.session.commit()
        flash("Project added.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("project_form.html", project=None)

@app.route("/admin/projects/<int:project_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == "POST":
        project.title = request.form.get("title", "").strip()
        project.slug = unique_slug(project.title, project.id)
        project.summary = request.form.get("summary", "").strip()
        project.description = request.form.get("description", "").strip()
        project.technologies = request.form.get("technologies", "").strip()
        project.github_url = request.form.get("github_url", "").strip()
        project.live_url = request.form.get("live_url", "").strip()
        project.featured = bool(request.form.get("featured"))

        image = request.files.get("image")
        if image and image.filename:
            if not allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
                flash("Unsupported image format.", "error")
                return render_template("project_form.html", project=project)
            image_name = f"{datetime.utcnow().timestamp()}-{secure_filename(image.filename)}"
            image.save(UPLOAD_DIR / image_name)
            project.image_filename = image_name

        document = request.files.get("document")
        if document and document.filename:
            if not allowed_file(document.filename, ALLOWED_DOC_EXTENSIONS):
                flash("Unsupported document format.", "error")
                return render_template("project_form.html", project=project)
            doc_name = f"{datetime.utcnow().timestamp()}-{secure_filename(document.filename)}"
            document.save(UPLOAD_DIR / doc_name)
            project.document_filename = doc_name

        db.session.commit()
        flash("Project updated.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("project_form.html", project=project)

@app.route("/admin/projects/<int:project_id>/delete", methods=["POST"])
@admin_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/site-settings", methods=["GET", "POST"])
@admin_required
def site_settings():
    settings = get_site_settings()

    if request.method == "POST":
        settings.hero_eyebrow = request.form.get("hero_eyebrow", "").strip()
        settings.hero_title = request.form.get("hero_title", "").strip()
        settings.hero_text = request.form.get("hero_text", "").strip()
        settings.about_eyebrow = request.form.get("about_eyebrow", "").strip()
        settings.about_title = request.form.get("about_title", "").strip()
        settings.about_paragraph_one = request.form.get("about_paragraph_one", "").strip()
        settings.about_paragraph_two = request.form.get("about_paragraph_two", "").strip()

        db.session.commit()
        flash("Homepage content updated.", "success")
        return redirect(url_for("site_settings"))

    return render_template("site_settings.html", settings=settings)

@app.errorhandler(413)
def too_large(_):
    return "Upload too large. Maximum size is 20 MB.", 413

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
