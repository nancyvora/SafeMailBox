import os, re, io, subprocess, bleach, requests, tempfile
from flask import flash, redirect, url_for
from flask import Flask, render_template, request, redirect, url_for, session, Response, send_file
from markupsafe import Markup
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash
from email_fetcher import fetch_and_store_emails
from models import Attachment, Email, db, User, FeedbackLog
from phishing_log import log_user_feedback
from datetime import datetime
from sqlalchemy import text
import requests
from bs4 import BeautifulSoup
from flask import url_for


app = Flask(__name__, instance_relative_config=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'emails.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "super_secret_key"

db.init_app(app)
with app.app_context():
    conn = db.engine.connect()
    conn.execute(text("PRAGMA journal_mode=WAL;"))
    conn.close()

# -------------------------------
# JINJA FILTERS
# -------------------------------
ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union(["br", "a", "p", "img"])
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height", "style"]
}

def sanitize_and_linkify(text):
    url_pattern = re.compile(r'(https?://[^\s]+)')
    linked_text = url_pattern.sub(r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', text)
    safe_html = bleach.clean(linked_text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    return Markup(safe_html)

@app.template_filter('safe_links')
def safe_links_filter(text):
    return sanitize_and_linkify(text)

@app.template_filter('nl2br')
def nl2br_filter(text):
    return Markup(text.replace('\n', '<br>\n'))

# -------------------------------
# ROUTES
# -------------------------------
@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    form_email = request.form.get("email")
    form_password = request.form.get("password")
    user = User.query.filter_by(email=form_email).first()

    if user and check_password_hash(user.password, form_password):
        session["email"] = user.email
        session["password"] = form_password
        fetch_and_store_emails(user.email, form_password, app)
        return redirect(url_for("inbox"))
    else:
        return "<h3>Invalid credentials</h3><a href='/'>Try again</a>"
    
def rewrite_cid_links(html_body):
    soup = BeautifulSoup(html_body, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src.startswith("cid:"):
            cid = src[4:].strip("<>")  # Remove cid: and <>
            img['src'] = url_for("inline_cid_image", cid=cid)
    return str(soup)

@app.route("/cid-image/<cid>")
def inline_cid_image(cid):
    attachment = Attachment.query.filter(Attachment.content_id == cid).first_or_404()
    return Response(attachment.data, mimetype=attachment.content_type)

@app.route("/inbox")
def inbox():
    user_email = session.get("email")
    if not user_email:
        return redirect(url_for("home"))
    emails = Email.query.filter_by(user_email=user_email).order_by(Email.date.desc()).all()
    return render_template("inbox.html", emails=emails, user=user_email)

@app.route("/refresh", methods=["POST"])
def refresh_inbox():
    user_email = session.get("email")
    user_password = session.get("password")
    if not user_email or not user_password:
        return redirect(url_for("home"))
    fetch_and_store_emails(user_email, user_password, app)
    return redirect(url_for("inbox"))

@app.route("/email/<int:email_id>")
def view_email(email_id):
    user_email = session.get("email")
    if not user_email:
        return redirect(url_for("home"))

    email = Email.query.options(joinedload(Email.attachments)).filter_by(id=email_id, user_email=user_email).first()

    if not email:
        return "<h3>Email not found or unauthorized</h3>"
 
    
    return render_template("view_email.html", email=email)

@app.route("/image-proxy")
def image_proxy():
    import urllib.parse
    url = request.args.get("url")
    if not url:
        return "Missing URL", 400
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return "Invalid URL", 400
    try:
        resp = requests.get(url, timeout=5)
        content_type = resp.headers.get("Content-Type", "image/png")
        return Response(resp.content, content_type=content_type)
    except Exception as e:
        print("Image proxy error:", e)
        return "", 404

@app.route("/email/<int:email_id>/feedback", methods=["POST"])
def submit_feedback(email_id):
    user_email = session.get("email")
    if not user_email:
        return redirect(url_for("home"))

    email_obj = Email.query.filter_by(id=email_id, user_email=user_email).first()
    if not email_obj:
        return "<h3>Unauthorized</h3>"

    feedback = request.form.get("feedback")
    email_obj.feedback = feedback  # store user's feedback

    # Flag email if user disagrees with model
    email_obj.flagged_for_review = (
        (feedback == "phishing" and not email_obj.is_phishing) or
        (feedback == "safe" and email_obj.is_phishing)
    )

    # Log into FeedbackLog
    feedback_entry = FeedbackLog(
        email_id=email_obj.id,
        user_email=user_email,
        feedback=feedback,
        model_prediction='phishing' if email_obj.is_phishing else 'safe',
        confidence=email_obj.confidence,
        timestamp=datetime.utcnow()
    )

    try:
        db.session.add(feedback_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("Database error while logging feedback:", e)

    # Also log to CSV
    log_user_feedback(
        email_id=email_obj.id,
        user_email=user_email,
        subject=email_obj.subject,
        model_prediction='phishing' if email_obj.is_phishing else 'safe',
        user_feedback=feedback,
        confidence=email_obj.confidence
    )

    return redirect(url_for("view_email", email_id=email_id))

@app.route("/attachment/<int:attachment_id>/download")
def download_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    return send_file(
        io.BytesIO(attachment.data),
        mimetype=attachment.content_type,
        as_attachment=True,
        download_name=attachment.filename
    )


@app.route("/attachment/<int:attachment_id>/scan")
def scan_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)

    # Save the attachment temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(attachment.filename)[-1]) as temp_file:
        temp_file.write(attachment.data)
        temp_file_path = temp_file.name

    try:
        # Send file to Dockerized YARA scanner
        with open(temp_file_path, "rb") as f:
            files = {'file': (attachment.filename, f)}
            response = requests.post("http://localhost:5001/scan", files=files)

        if response.status_code == 200:
            result = response.json()
            matches = result.get("matches", [])
            if matches:
                msg = f"Scan completed for {attachment.filename}. Threats found:\n\n" + "\n".join(matches)
            else:
                msg = f"Scan completed for {attachment.filename}. No vulnerabilities found."
        else:
            msg = f"Scan failed for {attachment.filename}. Scanner returned error."

        flash(msg, "scan_result")
        return redirect(url_for("view_email", email_id=attachment.email_id))

    except Exception as e:
        flash(f"Scan failed: {str(e)}", "scan_result")
        return redirect(url_for("view_email", email_id=attachment.email_id))

    finally:
        os.remove(temp_file_path)

from flask import Response, render_template_string

@app.route("/attachment/<int:attachment_id>/sandbox", methods=["POST"])
def sandbox_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=attachment.filename[-4:]) as temp_file:
        temp_file.write(attachment.data)
        temp_path = temp_file.name

    try:
        with open(temp_path, 'rb') as f:
            response = requests.post('http://localhost:5002/render', files={'file': f})

        if response.status_code == 200:
            return Response(response.content, mimetype=response.headers.get('Content-Type'))
        else:
            return f"Sandbox error: {response.text}", 500
    finally:
        os.remove(temp_path)

if __name__ == "__main__":
    app.run(debug=True)
