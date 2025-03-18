# app.py
from flask import Flask
from flask_login import LoginManager
from db import db
import os
from routes import main

# Initialize the Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Replace with a secure key
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'mydatabase.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Set up Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'main.login'  # Reference the blueprint route

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import Admin, Worker
    admin = db.session.get(Admin, int(user_id))  # Updated to Session.get
    if admin:
        return admin
    worker = db.session.get(Worker, int(user_id))  # Updated to Session.get
    if worker:
        return worker
    return None

    

# Import and register the blueprint from routes.py
app.register_blueprint(main)

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)