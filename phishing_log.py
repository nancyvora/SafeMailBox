import csv
import os
from datetime import datetime

LOG_FILE = "feedback_log.csv"

def log_user_feedback(email_id, user_email, subject, model_prediction, user_feedback, confidence):
    file_exists = os.path.exists(LOG_FILE)

    with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "timestamp", "email_id", "user_email", "subject",
                "model_prediction", "user_feedback", "confidence"
            ])

        writer.writerow([
            datetime.now().isoformat(),
            email_id,
            user_email,
            subject,
            model_prediction,
            user_feedback,
            round(confidence, 2)
        ])
