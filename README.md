# SafeMailBox — Secure AI-Powered Email Viewer

**SafeMailBox** is a secure, ML-integrated email system designed to isolate threats, detect phishing, and safely handle attachments using Docker-based sandboxing. It protects users from phishing emails, malware, and tracking threats by combining email sanitization, real-time scanning, isolated viewing, and a self-improving feedback loop.

---

## Features

- Gmail IMAP integration (Inbox, Compose, Drafts)
- Phishing detection with TF-IDF + Logistic Regression
- Feedback loop for real-world model refinement
- HTML sanitization using bleach and BeautifulSoup
- Secure CID inline image rendering
- Docker-based antivirus scanning of attachments
- Secure viewing of attachments in separate Docker containers
- Password are stored using hashing 

---

## Tech Stack

- **Backend**: Flask, Python, SQLAlchemy, IMAPClient
- **ML**: Scikit-learn, TF-IDF, Logistic Regression, Joblib
- **Security**: Docker, Windows Defender (PowerShell), bleach
- **Frontend**: Jinja2 templates + Classic UI styling
- **Database**: SQLite with per-user email segregation

---

## Security Architecture

SafeMailBox uses **process isolation, static rendering, and content sanitization** to secure every layer of email interaction.

### 1. HTML Email Sanitization
- Sanitized using `bleach` and `BeautifulSoup`
- Removes `<script>`, `<iframe>`, inline JS, and tracking links
- Styles are relocated to `<head>` to avoid rendering issues

### 2. CID Image Handling
- Embedded `cid:` images are securely extracted and rendered inline
- Remote/external images are stripped to avoid tracking and malicious injection

---

## Docker-Based Threat Isolation (Scan + View)

SafeMailBox uses **separate Docker containers for each operation** to ensure complete isolation and zero persistence between tasks.

### 1. Scanning in a Dedicated Docker Container
- When an attachment is received:
  - A **temporary container** is launched
  - The file is scanned using **Windows Defender**
  - Results are returned to Flask
  - The container is **destroyed immediately after the scan**

> This ensures malware is sandboxed during the scanning process, completely isolated from the host system.

---

### 2. Viewing in a Separate Docker Container
- If the scan passes:
  - A **new container** is spun up for viewing
  - The attachment is rendered using safe tools (LibreOffice, PyMuPDF, Pillow, etc.)
  - The file is converted to static HTML/image/PDF output
  - Only the rendered view is shown in the browser
  - The container is shut down immediately after use

> This protects against exploits hidden in document macros, scripts, or malformed files — nothing runs on the host.

| Operation | Container        | Purpose                         |
|-----------|------------------|---------------------------------|
| Scanning  | `scan_container` | Malware detection (isolated)   |
| Viewing   | `view_container` | Safe rendering (read-only)     |

This **double-container sandbox model** provides best-in-class isolation for all attachment handling.

---

## Feedback Loop for Phishing Detection

The phishing detector uses traditional ML:
- **Model**: TF-IDF + Logistic Regression
- **Input**: Email subject + body
- **Output**: Safe or Phishing label

### How Feedback Works:
1. Email is labeled automatically (safe or phishing)
2. User may override with:
   - **Mark as Safe**
   - **Mark as Phishing**
3. Feedback is logged with:
   - Model prediction, user response, email metadata
4. Stored in `feedback_log.csv`
5. Used to retrain the model and improve performance

## Setup Instructions

### 1. Add Your Email Credentials

Add email address and app password in the insert_user.py 

### 2. Initialize the Database

python setup_db.py
python models.py
python insert_user.py

### 3. Fetch Emails 

python email_fetcher.py

This will:

Connect to Gmail inbox via IMAP
Fetch and sanitize HTML
Extract inline CID images
Store emails and attachments

### 4. Run the Flask Web App

python app.py

### 5. Export Feedback for Retraining

python feedback_export.py

*start your docker before proceeding for the below commands*

### 6. Docker: Attachment Scanner

docker build -t yara-scanner .
docker run -d -p 5001:5000 --name yara-scanner yara-scanner #assuming your local webiste is on port 5000

### 7. Docker: Attachment Viewer

docker build -t sandbox-viewer viewer-docker/
docker run -d -p 5002:5000 --name sandbox-viewer sandbox-viewer

## Visuals 

<img width="959" height="471" alt="image" src="https://github.com/user-attachments/assets/40459b95-77a5-4c94-b023-dd4935dfbf2e" />
<img width="1919" height="880" alt="Screenshot 2025-07-12 094334" src="https://github.com/user-attachments/assets/913db206-cc6a-4f62-bf88-19cf133d4900" />
<img width="959" height="437" alt="image" src="https://github.com/user-attachments/assets/e063f6ff-604b-482d-91ed-87cab32de9e2" />
<img width="1915" height="930" alt="Screenshot 2025-07-11 224105" src="https://github.com/user-attachments/assets/81013347-c7a5-4f5a-ad9e-38980747f2ed" />
<img width="1919" height="947" alt="Screenshot 2025-07-11 224123" src="https://github.com/user-attachments/assets/8ebc848a-df15-41dd-8eed-98edb9ebf278" />



