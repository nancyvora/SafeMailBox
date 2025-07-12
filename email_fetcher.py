import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import base64
import bleach
from bleach.css_sanitizer import CSSSanitizer

from models import Email, Attachment, db
from phishing_detector import detect_phishing

# ----- Allowed HTML, Attributes & Styles -----
ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union([
    "p", "br", "a", "b", "i", "u", "strong", "em", "font", "span", "div", "img"
])
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "span": ["style"],
    "div": ["style"],
    "font": ["color", "face", "size"],
    "img": ["src", "alt", "style", "width", "height"]
}
ALLOWED_STYLES = [
    "color", "font-weight", "font-size", "font-family",
    "background-color", "text-align", "width", "height", "border-radius"
]
css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_STYLES)

# ----- Helpers -----
def extract_preview(html_body):
    text = BeautifulSoup(html_body, "html.parser").get_text()
    return text.strip().replace('\n', ' ')[:300]

def extract_cid_images(msg):
    cid_map = {}
    for part in msg.walk():
        content_id = part.get("Content-ID")
        content_type = part.get_content_type()
        if content_id and content_type.startswith("image/"):
            cid = content_id.strip("<>")
            payload = part.get_payload(decode=True)
            if payload:
                b64_data = base64.b64encode(payload).decode("utf-8")
                cid_map[cid] = f"data:{content_type};base64,{b64_data}"
    return cid_map

def extract_attachments(msg, email_record):
    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition", ""))
        if "attachment" in content_disposition.lower():
            filename = part.get_filename()
            if filename:
                decoded_filename = decode_header(filename)[0][0]
                if isinstance(decoded_filename, bytes):
                    decoded_filename = decoded_filename.decode(errors="ignore")
                payload = part.get_payload(decode=True)
                if payload:
                    attachment = Attachment(
                        email_id=email_record.id,
                        filename=decoded_filename,
                        content_type=part.get_content_type(),
                        data=payload
                    )
                    db.session.add(attachment)

# ----- Main Fetcher -----
def fetch_and_store_emails(user_email, password, app):
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(user_email, password)
    except Exception as e:
        print("[ERROR] Login failed:", e)
        return

    imap.select("inbox")
    status, messages = imap.search(None, "ALL")
    if status != "OK":
        print("[ERROR] Failed to fetch emails.")
        return

    mail_ids = messages[0].split()

    with app.app_context():
        for mail_id in reversed(mail_ids[-10:]):  # Fetch latest 10 emails
            try:
                _, msg_data = imap.fetch(mail_id, "(RFC822)")
            except Exception as e:
                print("[ERROR] Fetch failed:", e)
                continue

            for response_part in msg_data:
                if not isinstance(response_part, tuple):
                    continue

                try:
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_header(msg.get("Subject", ""))[0][0]
                    subject = subject.decode() if isinstance(subject, bytes) else subject or "(No Subject)"

                    from_email = decode_header(msg.get("From", ""))[0][0]
                    from_email = from_email.decode() if isinstance(from_email, bytes) else from_email or "(Unknown Sender)"
                    date = msg.get("Date", "(Unknown Date)")

                    body = ""
                    html_body = ""
                    has_attachments = False

                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition", "")).lower()

                            if "attachment" in content_disposition:
                                has_attachments = True
                                continue

                            payload = part.get_payload(decode=True)
                            if not payload:
                                continue

                            decoded = payload.decode(errors="ignore")

                            if content_type == "text/html":
                                html_body = decoded
                            elif content_type == "text/plain" and not html_body:
                                body = decoded
                    else:
                        content_type = msg.get_content_type()
                        decoded = msg.get_payload(decode=True).decode(errors="ignore")
                        if content_type == "text/html":
                            html_body = decoded
                        else:
                            body = decoded

                    # Inject inline CID images
                    cid_images = extract_cid_images(msg)
                    for cid, data_uri in cid_images.items():
                        if html_body:
                            html_body = html_body.replace(f"cid:{cid}", data_uri)

                    final_html = html_body if html_body else f"<pre>{body}</pre>"

                    # Sanitize for display
                    sanitized_html = bleach.clean(
                        final_html,
                        tags=ALLOWED_TAGS,
                        attributes=ALLOWED_ATTRIBUTES,
                        css_sanitizer=css_sanitizer,
                        strip=True
                    )

                    preview = extract_preview(sanitized_html)
                    phishing_result = detect_phishing(body if body else html_body)
                    is_phishing = phishing_result["is_phishing"]
                    confidence = phishing_result["score"]

                    exists = Email.query.filter_by(
                        user_email=user_email,
                        from_email=from_email,
                        subject=subject,
                        date=date
                    ).first()

                    if not exists:
                        new_email = Email(
                            user_email=user_email,
                            from_email=from_email,
                            sender=from_email,
                            subject=subject,
                            date=date,
                            body=sanitized_html,
                            preview=preview,
                            contains_attachment=has_attachments,
                            is_phishing=is_phishing,
                            confidence=confidence
                        )
                        db.session.add(new_email)
                        db.session.flush()  # Make new_email.id available

                        # Now extract and save attachments
                        extract_attachments(msg, new_email)

                except Exception as e:
                    print("[ERROR] Email parse failed:", e)

        try:
            db.session.commit()
        except Exception as db_error:
            db.session.rollback()
            print("[ERROR] DB commit failed:", db_error)

    imap.logout()
