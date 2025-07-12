from models import db, Email
from app import app
import pandas as pd

with app.app_context():
    data = Email.query.filter(Email.feedback != None).all()
    rows = [{
        "subject": e.subject,
        "body": e.body,
        "label": 1 if e.feedback == "phishing" else 0
    } for e in data]

    df = pd.DataFrame(rows)
    df.to_csv("feedback_dataset.csv", index=False)
    print("Feedback exported.")

for e in data:
    e.used_for_training = True
db.session.commit()