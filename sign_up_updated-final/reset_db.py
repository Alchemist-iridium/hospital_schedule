# reset_database.py
from flask import Flask
from db import db
from models import *  # Import models to register them with db
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'mydatabase.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def reset_database():
    with app.app_context():
        db_path = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"Resetting database at: {db_path}")
        db.drop_all()
        print("All tables dropped.")
        db.create_all()
        print("All tables recreated successfully.")
        # Verify the database file exists and is accessible
        db_file = os.path.join(basedir, 'mydatabase.db')
        if os.path.exists(db_file):
            print(f"Database file confirmed at: {db_file}")
        else:
            print("Warning: Database file not found after reset!")

if __name__ == "__main__":
    reset_database()