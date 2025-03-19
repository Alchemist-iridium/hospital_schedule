# create_admin.py
from models import db, Admin
from flask import Flask
from sqlalchemy.exc import IntegrityError
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'mydatabase.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

def create_admin():
    try:
        admin_id = int(input("Enter admin ID: "))
        name = input("Enter admin name: ")
        password = input("Enter admin password: ")
        admin = Admin(id=admin_id, name=name)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin '{name}' created successfully with ID: {admin_id}")
    except ValueError:
        print("Error: ID must be an integer.")
    except IntegrityError:
        db.session.rollback()
        print(f"Error: Admin ID {admin_id} already exists. Please choose a unique ID.")

if __name__ == "__main__":
    with app.app_context():
        create_admin()