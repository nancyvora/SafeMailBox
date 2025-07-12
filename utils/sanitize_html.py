# utils/sanitize_html.py
from bs4 import BeautifulSoup

def sanitize_email_body(body):
    try:
        soup = BeautifulSoup(body, "html.parser")
        return soup.get_text()
    except Exception:
        return body  # fallback if sanitization fails
