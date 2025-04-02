# models.py
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from db import db

# Create the database object



# Workgroup Model
# New model to manage groups of workers
class Workgroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., "Group A"
    max_senior_workers = db.Column(db.Integer, nullable=False)  # Max senior workers allowed
    max_junior_workers = db.Column(db.Integer, nullable=False)  # Max junior workers allowed

    
    intervals = db.relationship('Interval', backref='workgroup', lazy=True)  # Intervals for this group
    schedules = db.relationship('Schedule', backref='workgroup', lazy=True)  # Schedules for this group



# WorkerSequence Model
class WorkerSequence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    workgroup_id = db.Column(db.Integer, db.ForeignKey('workgroup.id'), nullable=False)
    in_group_initial_order = db.Column(db.Integer, nullable=True)
    current_score = db.Column(db.Float, nullable=True)
    sequence = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='initialized')

    workgroup = db.relationship('Workgroup', backref='worker_sequences', lazy=True)
    worker = db.relationship('Worker', back_populates='sequences')


    @property
    def worker_name(self):
        return self.worker.name if self.worker else None

    def calculate_priority(self, w):
        """Calculate priority score: traded_points + w * (max_initial_order - in_group_initial_order + 1)"""
        worker = Worker.query.get(self.worker_id)
        workgroup = Workgroup.query.get(self.workgroup_id)
        max_initial_order = workgroup.max_senior_workers if self.type == 'senior' else workgroup.max_junior_workers
        base_points = max_initial_order - (self.in_group_initial_order or 0) + 1
        self.current_score = round(worker.traded_points + w * base_points,3)
        return self.current_score
    

# Shift Model
class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    type = db.Column(db.String(50), nullable=False)  # e.g., "A"
    day = db.Column(db.Integer, nullable=False) 
    end_day = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)  # e.g., 7:00 AM
    end_time = db.Column(db.Time, nullable=False)    # e.g., 7:00 PM
    points = db.Column(db.Integer, default=0)  # Points for taking this shift
    
    schedules = db.relationship('Schedule', backref='shift', lazy=True)
    


# Interval Model
# Now linked to Workgroup instead of just Shift directly
class Interval(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    workgroup_id = db.Column(db.Integer, db.ForeignKey('workgroup.id'), nullable=False)
    day = db.Column(db.Integer, nullable=False) 
    end_day = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)  # e.g., 7:00 AM
    end_time = db.Column(db.Time, nullable=False)    # e.g., 9:00 AM
    max_senior_workers = db.Column(db.Integer, nullable=False)  # Max senior workers for this interval
    max_junior_workers = db.Column(db.Integer, nullable=False)  # Max junior workers for this interval
    current_senior_workers = db.Column(db.Integer, default=0)  # Current senior workers
    current_junior_workers = db.Column(db.Integer, default=0)  # Current junior workers



class ShiftInterval(db.Model):
    __tablename__ = 'shift_interval'
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), primary_key=True)
    workgroup_id = db.Column(db.Integer, db.ForeignKey('workgroup.id'), primary_key=True)
    interval_id = db.Column(db.Integer, db.ForeignKey('interval.id'), primary_key=True)

    shift = db.relationship('Shift', backref='shift_intervals')
    workgroup = db.relationship('Workgroup', backref='shift_intervals')
    interval = db.relationship('Interval', backref='shift_intervals')




# Schedule Model
# Now linked to Workgroup too
class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False)
    workgroup_id = db.Column(db.Integer, db.ForeignKey('workgroup.id'), nullable=False)


# Worker Model
# Now linked to Workgroup
class Worker(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='worker')
    type = db.Column(db.String(10), nullable=False)
    initial_order = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, default=0)
    traded_points = db.Column(db.Integer, default=0)
    password_hash = db.Column(db.String(128), nullable=False)
    
    schedules = db.relationship('Schedule', backref='worker', lazy=True)
    sequences = db.relationship('WorkerSequence', back_populates='worker', lazy=True)


    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)




# Admin Model
# No changes needed here
class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)  # Manual ID assignment
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), default="admin")
    password_hash = db.Column(db.String(128), nullable=False)
    operations = db.relationship('AdminOperationLog', backref='admin', lazy=True)  # Relationship to logs

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    


class AdminOperationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    operation = db.Column(db.String(50), nullable=False)  # e.g., "add", "edit", "delete", "batch_import"
    entity_type = db.Column(db.String(50), nullable=False)  # e.g., "worker", "interval"
    entity_id = db.Column(db.Integer, nullable=True)  # ID of the affected entity, if applicable
    details = db.Column(db.Text, nullable=True)  # Additional details (e.g., JSON of changes)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @staticmethod
    def log_operation(admin_id, operation, entity_type, entity_id=None, details=None):
        """Log an admin operation to the database."""
        log = AdminOperationLog(
            admin_id=admin_id,
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details
        )
        db.session.add(log)
        db.session.commit()





class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, nullable=False)  # Admin or Worker ID
    recipient_type = db.Column(db.String(10), nullable=False)  # "admin" or "worker"
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def send_notification(cls, recipient_id, recipient_type, message):
        notification = cls(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            message=message
        )
        db.session.add(notification)
        db.session.commit()