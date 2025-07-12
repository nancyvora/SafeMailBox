from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(255), db.ForeignKey('user.email'), nullable=False)
    from_email = db.Column(db.String(255))
    sender = db.Column(db.String(255))  # Full display name + email
    subject = db.Column(db.String(255))
    date = db.Column(db.String(100))
    body = db.Column(db.Text)
    preview = db.Column(db.String(512))  # Short snippet
    contains_attachment = db.Column(db.Boolean, default=False)
    is_phishing = db.Column(db.Boolean, default=False)
    confidence = db.Column(db.Float, default=0.0)
    feedback = db.Column(db.String(10))  # 'phishing', 'safe', or None
    flagged_for_review = db.Column(db.Boolean, default=False)

    feedback_logs = db.relationship('FeedbackLog', backref='email', lazy=True)
    attachments = db.relationship('Attachment', backref='email', lazy=True)

class FeedbackLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.Integer, db.ForeignKey('email.id'), nullable=False)
    user_email = db.Column(db.String(255), nullable=False)
    feedback = db.Column(db.String(10), nullable=False)  # 'phishing' or 'safe'
    model_prediction = db.Column(db.String(10), nullable=False)  # 'phishing' or 'safe'
    confidence = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.Integer, db.ForeignKey('email.id'), nullable=False)
    filename = db.Column(db.String(255))
    content_type = db.Column(db.String(100))
    data = db.Column(db.LargeBinary)
    content_id = db.Column(db.String(256))


