# insert_user.py
import os
from flask import Flask
from models import db, User
from werkzeug.security import generate_password_hash

app = Flask(__name__, instance_relative_config=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'emails.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    email = "enter here your email address"
    password = "enter here your app password"  # app password only

    hashed_password = generate_password_hash(password)

    if not User.query.filter_by(email=email).first():
        user = User(email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        print("Hashed user inserted.")
    else:
        print("User already exists.")

