import joblib
import os

# Path to the model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "phishing_model.joblib")

# Load tuple (model, vectorizer)
model, vectorizer = joblib.load(MODEL_PATH)

def detect_phishing(text):
    """
    Predict whether a given email text is phishing.
    Returns: {"is_phishing": True/False, "score": confidence}
    """
    X = vectorizer.transform([text])
    prediction = model.predict(X)[0]
    probas = model.predict_proba(X)[0]
    confidence = max(probas)

    return {
        "is_phishing": bool(prediction),
        "score": round(float(confidence), 3)
    }
