# routes.py (full file for clarity)
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, Response
from flask_login import login_user, logout_user, login_required, current_user
import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlalchemy import not_, asc
from models import *
from datetime import datetime
from db import db
from io import BytesIO, TextIOWrapper, StringIO
import csv




main = Blueprint('main', __name__)

# Helper to restrict access to admins
def admin_required(func):
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Access denied: Admins only.')
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@main.route('/')
def index():
    return redirect(url_for('main.login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('id')  # Use .get() to avoid KeyError
        password = request.form.get('password')
        print(f"Received ID: {user_id}, Password: {password}")  # Debug output
        
        if not user_id or not password:
            flash('Please enter both ID and password')
            return redirect(url_for('main.login'))
        
        try:
            user_id = int(user_id)  # Convert to integer
            print(f"Converted ID to int: {user_id}")  # Debug
        except ValueError:
            flash('ID must be a number')
            return redirect(url_for('main.login'))
        
        # Query Admin or Worker by ID
        user = Admin.query.get(user_id) or Worker.query.get(user_id)
        print(f"Queried user: {user}")  # Debug: Check if user is found
        
        if user and user.check_password(password):
            print(f"Password check passed for user: {user.name}")  # Debug
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('main.admin_dashboard'))
            else:
                return redirect(url_for('main.worker_dashboard'))  # Placeholder
        else:
            flash('Invalid ID or password')
            print(f"Login failed: User {user_id} not found or password incorrect")  # Debug
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))



@main.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('main.login'))
    # Count unread notifications for the admin
    unread_notifications = Notification.query.filter_by(
        recipient_id=current_user.id,
        recipient_type='admin'
    ).count()
    return render_template('admin/admin_dashboard.html', 
                          unread_notifications=unread_notifications)



@main.route('/admin/operation_log')
@admin_required
def admin_operation_log():
    # Query operations for the current admin, ordered by timestamp descending
    operations = AdminOperationLog.query.filter_by(admin_id=current_user.id).order_by(AdminOperationLog.timestamp.desc()).all()
    return render_template('admin/operation_log.html', operations=operations)







# --- Workgroups ---
@main.route('/admin/workgroups')
@admin_required
def manage_workgroups():
    workgroups = Workgroup.query.all()
    return render_template('admin/workgroups.html', workgroups=workgroups)





@main.route('/admin/workgroups/add', methods=['GET', 'POST'])
@admin_required
def add_workgroup():
    if request.method == 'POST':
        name = request.form['name']
        max_senior_workers = int(request.form['max_senior_workers'])
        max_junior_workers = int(request.form['max_junior_workers'])
        workgroup = Workgroup(name=name, max_senior_workers=max_senior_workers, max_junior_workers=max_junior_workers)
        db.session.add(workgroup)
        db.session.commit()
        
        AdminOperationLog.log_operation(
            admin_id=current_user.id,
            operation="add",
            entity_type="workgroup",
            entity_id=workgroup.id,
            details=f"Added workgroup: {name}"
        )
        
        flash('Workgroup added successfully.')
        return redirect(url_for('main.manage_workgroups'))
    return render_template('admin/workgroup_form.html', action='Add')




@main.route('/admin/workgroups/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_workgroup(id):
    workgroup = Workgroup.query.get_or_404(id)
    if request.method == 'POST':
        old_details = f"Name: {workgroup.name}, Max Senior: {workgroup.max_senior_workers}, Max Junior: {workgroup.max_junior_workers}"
        workgroup.name = request.form['name']
        workgroup.max_senior_workers = int(request.form['max_senior_workers'])
        workgroup.max_junior_workers = int(request.form['max_junior_workers'])
        db.session.commit()
        
        new_details = f"Name: {workgroup.name}, Max Senior: {workgroup.max_senior_workers}, Max Junior: {workgroup.max_junior_workers}"
        AdminOperationLog.log_operation(
            admin_id=current_user.id,
            operation="edit",
            entity_type="workgroup",
            entity_id=id,
            details=f"Changed from {old_details} to {new_details}"
        )
        
        flash('Workgroup updated successfully.')
        return redirect(url_for('main.manage_workgroups'))
    return render_template('admin/workgroup_form.html', action='Edit', workgroup=workgroup)




@main.route('/admin/workgroups/delete/<int:id>', methods=['POST'])
@admin_required
def delete_workgroup(id):
    workgroup = Workgroup.query.get_or_404(id)
    details = f"Name: {workgroup.name}, Max Senior: {workgroup.max_senior_workers}, Max Junior: {workgroup.max_junior_workers}"
    db.session.delete(workgroup)
    db.session.commit()
    
    AdminOperationLog.log_operation(
        admin_id=current_user.id,
        operation="delete",
        entity_type="workgroup",
        entity_id=id,
        details=f"Deleted workgroup: {details}"
    )
    
    flash('Workgroup deleted successfully.')
    return redirect(url_for('main.manage_workgroups'))



# --- Shifts ---
@main.route('/admin/shifts')
@admin_required
def manage_shifts():
    shifts = Shift.query.all()
    return render_template('admin/shifts.html', shifts=shifts)




@main.route('/admin/shifts/add', methods=['GET', 'POST'])
@admin_required
def add_shift():
    if request.method == 'POST':
        id = int(request.form['id'])
        type = request.form['type']
        day = int(request.form['day'])
        start_time_str = request.form['start_time']
        end_time_str = request.form['end_time']
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        end_day = day if end_time > start_time else (day % 7) + 1
        points = int(request.form['points'])
        shift = Shift(
            id = id,
            type=type,
            day=day,
            end_day=end_day,
            start_time=start_time,
            end_time=end_time,
            points=points
        )
        db.session.add(shift)
        db.session.commit()
        
        AdminOperationLog.log_operation(
            admin_id=current_user.id,
            operation="add",
            entity_type="shift",
            entity_id=shift.id,
            details=f"Added shift: {type}, Day: {day}, End Day: {end_day}, Start: {start_time}, End: {end_time}, Points: {points}"
        )
        
        flash('Shift added successfully.')
        return redirect(url_for('main.manage_shifts'))
    return render_template('admin/shift_form.html', action='Add')




@main.route('/admin/shifts/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_shift(id):
    shift = Shift.query.get_or_404(id)
    if request.method == 'POST':
        old_details = f"Type: {shift.type}, Day: {shift.day}, End Day: {shift.end_day}, Start: {shift.start_time}, End: {shift.end_time}, Points: {shift.points}"
        shift.type = request.form['type']
        shift.day = int(request.form['day'])
        start_time_str = request.form['start_time']
        end_time_str = request.form['end_time']
        shift.start_time = datetime.strptime(start_time_str, '%H:%M').time()
        shift.end_time = datetime.strptime(end_time_str, '%H:%M').time()
        shift.end_day = shift.day if shift.end_time > shift.start_time else (shift.day % 7) + 1
        shift.points = int(request.form['points'])
        db.session.commit()
        
        new_details = f"Type: {shift.type}, Day: {shift.day}, End Day: {shift.end_day}, Start: {shift.start_time}, End: {shift.end_time}, Points: {shift.points}"
        AdminOperationLog.log_operation(
            admin_id=current_user.id,
            operation="edit",
            entity_type="shift",
            entity_id=id,
            details=f"Changed from {old_details} to {new_details}"
        )

        flash('Shift updated successfully.')
        return redirect(url_for('main.manage_shifts'))
    return render_template('admin/shift_form.html', action='Edit', shift=shift)



@main.route('/admin/shifts/delete/<int:id>', methods=['POST'])
@admin_required
def delete_shift(id):
    shift = Shift.query.get_or_404(id)
    details = f"Type: {shift.type}, Day: {shift.day}, Start: {shift.start_time}, End: {shift.end_time}, Points: {shift.points}"
    db.session.delete(shift)
    db.session.commit()
    
    AdminOperationLog.log_operation(
        admin_id=current_user.id,
        operation="delete",
        entity_type="shift",
        entity_id=id,
        details=f"Deleted shift: {details}"
    )
    
    flash('Shift deleted successfully.')
    return redirect(url_for('main.manage_shifts'))


# Batch Import for Shifts
@main.route('/admin/shifts/import', methods=['GET', 'POST'])
@admin_required
def import_shifts():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded.')
            return redirect(url_for('main.import_shifts'))
        file = request.files['file']
        if not file.filename:
            flash('No file selected.')
            return redirect(url_for('main.import_shifts'))
        
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
                print(f"CSV DataFrame: {df}")
            elif file.filename.endswith('.xlsx'):
                df = pd.read_excel(file, header=1)  # Assuming header in row 2, adjust if needed
                print(f"XLSX DataFrame after header fix: {df}")
            else:
                flash('Unsupported file type.')
                return redirect(url_for('main.import_shifts'))
            
            if df.empty:
                flash('The uploaded file is empty.')
                return redirect(url_for('main.import_shifts'))
            
            required_columns = ['id','type', 'day', 'start_time', 'end_time', 'points']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                flash(f'Missing required columns: {", ".join(missing_columns)}')
                return redirect(url_for('main.import_shifts'))
            
            data = df.to_dict(orient='records')
            print(f"Data to preview: {data}")
            session['shift_import_data'] = data
            return render_template('admin/shift_import_preview.html', data=data)
        except Exception as e:
            flash(f'Error reading file: {str(e)}')
            return redirect(url_for('main.import_shifts'))
    return render_template('admin/shift_import.html')




@main.route('/admin/shifts/import/confirm', methods=['POST'])
@admin_required
def confirm_import_shifts():
    data = session.get('shift_import_data')
    if not data:
        flash('No import data found. Please upload a file again.')
        return redirect(url_for('main.import_shifts'))
    errors = []
    for row in data:
        try:
            start_time = datetime.strptime(str(row['start_time']), '%H:%M').time()
            end_time = datetime.strptime(str(row['end_time']), '%H:%M').time()
            day = int(row['day'])
            end_day = day if end_time > start_time else (day % 7) + 1
            shift = Shift(
                id=int(row['id']),
                type=row['type'],
                day=day,
                end_day=end_day,
                start_time=start_time,
                end_time=end_time,
                points=int(row['points'])
            )
            db.session.add(shift)
            db.session.commit()

            AdminOperationLog.log_operation(
                admin_id=current_user.id,
                operation="add",
                entity_type="shift",
                entity_id=shift.id,
                details=f"Batch import added shift: {shift.type}, Day: {shift.day}, End Day: {shift.end_day}, Start: {shift.start_time}, End: {shift.end_time}, Points: {shift.points}"
            )
        except Exception as e:
            db.session.rollback()
            errors.append(f"Error importing shift {row['type']}, day {row['day']}: {str(e)}")
    session.pop('shift_import_data', None)
    if errors:
        return render_template('admin/shift_import_result.html', errors=errors, success=False)
    return render_template('admin/shift_import_result.html', success=True, errors=None)

# --- Intervals ---
@main.route('/admin/intervals')
@admin_required
def manage_intervals():
    intervals = Interval.query.all()
    return render_template('admin/intervals.html', intervals=intervals)


@main.route('/admin/intervals/add', methods=['GET', 'POST'])
@admin_required
def add_interval():
    workgroups = Workgroup.query.all()
    if request.method == 'POST':
        id = int(request.form['id'])
        workgroup_id = int(request.form['workgroup_id'])
        type = int(request.form['type'])
        day = int(request.form['day'])
        start_time_str = request.form['start_time']
        end_time_str = request.form['end_time']
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        end_day = day if end_time > start_time else (day % 7) + 1
        max_senior_workers = int(request.form['max_senior_workers'])
        max_junior_workers = int(request.form['max_junior_workers'])
        interval = Interval(
            id = id,
            workgroup_id=workgroup_id,
            day=day,
            end_day=end_day,
            start_time=start_time,
            end_time=end_time,
            max_senior_workers=max_senior_workers,
            max_junior_workers=max_junior_workers
        )
        db.session.add(interval)
        db.session.commit()
        
        new_details = f"Workgroup: {interval.workgroup_id}, Day: {interval.day}, End Day: {interval.end_day}, Start: {interval.start_time}, End: {interval.end_time}"
        AdminOperationLog.log_operation(
            admin_id=current_user.id,
            operation="add",
            entity_type="interval",
            entity_id=interval.id,  # Use interval.id, not id
            details=f"Added interval: {new_details}"
        )
        
        flash('Interval added successfully.')
        return redirect(url_for('main.manage_intervals'))
    return render_template('admin/interval_form.html', action='Add', workgroups=workgroups)






@main.route('/admin/intervals/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_interval(id):
    interval = Interval.query.get_or_404(id)
    workgroups = Workgroup.query.all()
    if request.method == 'POST':
        old_details = f"Workgroup: {interval.workgroup_id}, Day: {interval.day}, End Day: {interval.end_day}, Start: {interval.start_time}, End: {interval.end_time}"
        interval.workgroup_id = int(request.form['workgroup_id'])
        interval.day = int(request.form['day'])
        start_time_str = request.form['start_time']
        end_time_str = request.form['end_time']
        interval.start_time = datetime.strptime(start_time_str, '%H:%M').time()
        interval.end_time = datetime.strptime(end_time_str, '%H:%M').time()
        interval.end_day = interval.day if interval.end_time > interval.start_time else (interval.day % 7) + 1
        interval.max_senior_workers = int(request.form['max_senior_workers'])
        interval.max_junior_workers = int(request.form['max_junior_workers'])
        db.session.commit()

        new_details = f"Workgroup: {interval.workgroup_id}, Day: {interval.day}, End Day: {interval.end_day}, Start: {interval.start_time}, End: {interval.end_time}"
        AdminOperationLog.log_operation(
            admin_id=current_user.id,
            operation="edit",
            entity_type="interval",
            entity_id=id,
            details=f"Changed from {old_details} to {new_details}"
        )
        
        flash('Interval updated successfully.')
        return redirect(url_for('main.manage_intervals'))
    return render_template('admin/interval_form.html', action='Edit', interval=interval, workgroups=workgroups)




@main.route('/admin/intervals/delete/<int:id>', methods=['POST'])
@admin_required
def delete_interval(id):
    interval = Interval.query.get_or_404(id)
    details = f"Workgroup: {interval.workgroup_id}, Day: {interval.day}, End Day: {interval.end_day}, Start: {interval.start_time}, End: {interval.end_time}"
    db.session.delete(interval)
    db.session.commit()
    
    AdminOperationLog.log_operation(
        admin_id=current_user.id,
        operation="delete",
        entity_type="interval",
        entity_id=id,
        details=f"Deleted interval: {details}"
    )
    
    flash('Interval deleted successfully.')
    return redirect(url_for('main.manage_intervals'))

# batch import for the intervals

@main.route('/admin/intervals/import', methods=['GET', 'POST'])
@admin_required
def import_intervals():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded.')
            return redirect(url_for('main.import_intervals'))
        file = request.files['file']
        if not file.filename:
            flash('No file selected.')
            return redirect(url_for('main.import_intervals'))
        
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
                print(f"CSV DataFrame: {df}")
            elif file.filename.endswith('.xlsx'):
                # Read Excel, specifying header row (assuming row 1, index 0-based)
                df = pd.read_excel(file, header=1)
                print(f"XLSX DataFrame after header fix: {df}")
            else:
                flash('Unsupported file type.')
                return redirect(url_for('main.import_intervals'))
            
            if df.empty:
                flash('The uploaded file is empty.')
                return redirect(url_for('main.import_intervals'))
            
            # Ensure required columns are present
            required_columns = ['id','workgroup_id', 'day', 'start_time', 'end_time', 'max_senior_workers', 'max_junior_workers']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                flash(f'Missing required columns: {", ".join(missing_columns)}')
                return redirect(url_for('main.import_intervals'))
            
            data = df.to_dict(orient='records')
            print(f"Data to preview: {data}")
            session['interval_import_data'] = data
            return render_template('admin/interval_import_preview.html', data=data)
        except Exception as e:
            flash(f'Error reading file: {str(e)}')
            return redirect(url_for('main.import_intervals'))
    return render_template('admin/interval_import.html')




@main.route('/admin/intervals/import/confirm', methods=['POST'])
@admin_required
def confirm_import_intervals():
    data = session.get('interval_import_data')
    if not data:
        flash('No import data found. Please upload a file again.')
        return redirect(url_for('main.import_intervals'))
    errors = []
    for row in data:
        try:
            start_time = datetime.strptime(str(row['start_time']), '%H:%M').time()
            end_time = datetime.strptime(str(row['end_time']), '%H:%M').time()
            day = int(row['day'])
            end_day = day if end_time > start_time else (day % 7) + 1
            interval = Interval(
                id=int(row['id']),
                workgroup_id=int(row['workgroup_id']),
                day=day,
                start_time=start_time,
                end_day=end_day,
                end_time=end_time,
                max_senior_workers=int(row['max_senior_workers']),
                max_junior_workers=int(row['max_junior_workers'])
            )
            db.session.add(interval)
            db.session.commit()
            
            details = f"Workgroup: {interval.workgroup_id}, Day: {interval.day}, End Day: {interval.end_day}, Start: {interval.start_time}, End: {interval.end_time}"
            AdminOperationLog.log_operation(
                admin_id=current_user.id,
                operation="add",
                entity_type="interval",
                entity_id=interval.id,
                details=f"Batch import added interval: {details}"
            )
        except Exception as e:
            db.session.rollback()
            errors.append(f"Error importing interval for workgroup {row['workgroup_id']}, day {row['day']}: {str(e)}")
    session.pop('interval_import_data', None)
    if errors:
        return render_template('admin/interval_import_result.html', errors=errors, success=False)
    return render_template('admin/interval_import_result.html', success=True, errors=None)


# --- Shift_Interval relationship ---




# Display and manage shift-interval relationships
@main.route('/admin/shift_interval_management')
@admin_required
def shift_interval_management():
    # Fetch all shifts, intervals, and workgroups for dropdowns
    shifts = Shift.query.all()
    intervals = Interval.query.all()
    workgroups = Workgroup.query.all()
    
    # Fetch all current relationships with joined data
    relationships = db.session.query(ShiftInterval, Shift, Interval, Workgroup)\
        .join(Shift, Shift.id == ShiftInterval.shift_id)\
        .join(Interval, Interval.id == ShiftInterval.interval_id)\
        .join(Workgroup, Workgroup.id == ShiftInterval.workgroup_id).all()
    
    return render_template('admin/shift_interval_management.html', 
                          shifts=shifts, 
                          intervals=intervals, 
                          workgroups=workgroups,
                          relationships=relationships)





# Add a new shift-interval relationship
@main.route('/admin/shift_interval_management/add', methods=['POST'])
@admin_required
def add_shift_interval():
    shift_id = int(request.form['shift_id'])
    workgroup_id = int(request.form['workgroup_id'])
    interval_id = int(request.form['interval_id'])
    
    # Validate that the interval belongs to the selected workgroup
    interval = Interval.query.get(interval_id)
    if not interval or interval.workgroup_id != workgroup_id:
        flash('Selected interval does not belong to the selected workgroup.', 'error')
        return redirect(url_for('main.shift_interval_management'))
    
    # Check if the relationship already exists
    exists = ShiftInterval.query.filter_by(
        shift_id=shift_id,
        workgroup_id=workgroup_id,
        interval_id=interval_id
    ).first()
    if exists:
        flash('This shift-workgroup-interval relationship already exists.', 'error')
    else:
        new_relationship = ShiftInterval(
            shift_id=shift_id,
            workgroup_id=workgroup_id,
            interval_id=interval_id
        )
        db.session.add(new_relationship)
        db.session.commit()
        flash('Relationship added successfully.', 'success')
    
    return redirect(url_for('main.shift_interval_management'))





# Delete an existing shift-interval relationship
@main.route('/admin/shift_interval_management/delete', methods=['POST'])
@admin_required
def delete_shift_interval():
    shift_id = int(request.form['shift_id'])
    workgroup_id = int(request.form['workgroup_id'])
    interval_id = int(request.form['interval_id'])
    
    # Delete the relationship
    ShiftInterval.query.filter_by(
        shift_id=shift_id,
        workgroup_id=workgroup_id,
        interval_id=interval_id
    ).delete()
    db.session.commit()
    flash('Relationship deleted successfully.', 'success')
    
    return redirect(url_for('main.shift_interval_management'))




# Batch import shift-interval relationships
@main.route('/admin/shift_interval_import', methods=['GET', 'POST'])
@admin_required
def shift_interval_import():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded.', 'error')
            return redirect(url_for('main.shift_interval_import'))
        
        file = request.files['file']
        if not file.filename:
            flash('No file selected.', 'error')
            return redirect(url_for('main.shift_interval_import'))
        
        try:
            # Read file based on extension
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith('.xlsx'):
                # Specify header row (second row, index 1) and use openpyxl engine
                df = pd.read_excel(file, engine='openpyxl', header=1)
                # Normalize column names to handle spaces or case issues
                df.columns = df.columns.str.strip().str.lower()
            else:
                flash('Unsupported file type. Use CSV or XLSX.', 'error')
                return redirect(url_for('main.shift_interval_import'))
            
            # Validate column names
            required_columns = ['shift_id', 'workgroup_id', 'interval_id']
            if not all(col in df.columns for col in required_columns):
                flash('File must contain "shift_id", "workgroup_id", and "interval_id" columns.', 'error')
                return redirect(url_for('main.shift_interval_import'))
            
            # Remove duplicates within the file itself
            df = df.drop_duplicates(subset=['shift_id', 'workgroup_id', 'interval_id'])
            
            # Convert DataFrame columns to integers, handling any non-numeric values
            for col in required_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce', downcast='integer')
            # Drop rows with NaN after conversion (invalid IDs)
            df = df.dropna(subset=required_columns)
            
            # Fetch valid IDs
            shift_ids = set(s.id for s in Shift.query.all())
            workgroup_ids = set(w.id for w in Workgroup.query.all())
            interval_ids = set(i.id for i in Interval.query.all())
            
            # Validate workgroup_id matches interval's workgroup_id
            interval_workgroups = {i.id: i.workgroup_id for i in Interval.query.all()}
            
            # Fetch existing relationships as a set of tuples
            existing_pairs = set(
                (s.shift_id, s.workgroup_id, s.interval_id) for s in ShiftInterval.query.all()
            )
            
            new_relationships = []
            errors = []
            for index, row in df.iterrows():
                shift_id = int(row['shift_id'])
                workgroup_id = int(row['workgroup_id'])
                interval_id = int(row['interval_id'])
                
                # Validation checks
                if shift_id not in shift_ids:
                    errors.append(f"Invalid shift_id {shift_id} at row {index+2}")
                elif workgroup_id not in workgroup_ids:
                    errors.append(f"Invalid workgroup_id {workgroup_id} at row {index+2}")
                elif interval_id not in interval_ids:
                    errors.append(f"Invalid interval_id {interval_id} at row {index+2}")
                elif interval_workgroups.get(interval_id) != workgroup_id:
                    errors.append(f"Interval {interval_id} does not belong to workgroup {workgroup_id} at row {index+2}")
                elif (shift_id, workgroup_id, interval_id) in existing_pairs:
                    continue  # Silently skip existing relationships
                else:
                    new_relationships.append((shift_id, workgroup_id, interval_id))
                    existing_pairs.add((shift_id, workgroup_id, interval_id))  # Update in-memory set
            
            if errors:
                flash('Errors in file: ' + ', '.join(errors), 'error')
            
            if new_relationships:
                # Insert new relationships one-by-one to avoid bulk insert issues
                for shift_id, workgroup_id, interval_id in new_relationships:
                    new_relationship = ShiftInterval(
                        shift_id=shift_id,
                        workgroup_id=workgroup_id,
                        interval_id=interval_id
                    )
                    db.session.add(new_relationship)
                    try:
                        db.session.commit()  # Commit each record individually
                    except Exception as e:
                        db.session.rollback()
                        errors.append(f"Failed to insert ({shift_id}, {workgroup_id}, {interval_id}): {str(e)}")
                
                if not errors:
                    flash(f'Successfully imported {len(new_relationships)} new relationships.', 'success')
                else:
                    flash('Some relationships failed to import: ' + ', '.join(errors), 'error')
            elif not errors:
                flash('No new relationships to import.', 'info')
        
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
        
        return redirect(url_for('main.shift_interval_management'))
    
    return render_template('admin/shift_interval_import.html')





# --- Workers ---
@main.route('/admin/workers')
@admin_required
def manage_workers():
    workers = Worker.query.all()
    return render_template('admin/workers.html', workers=workers)


@main.route('/admin/workers/add', methods=['GET', 'POST'])
@admin_required
def add_worker():
    if request.method == 'POST':
        try:
            id_ = int(request.form['id'])
            name = request.form['name']
            role = "worker"
            type_ = request.form['type']
            initial_order = int(request.form['initial_order'])
            password = request.form['password']
            worker = Worker(id=id_, name=name, role=role, type=type_, initial_order=initial_order)
            worker.set_password(password)
            db.session.add(worker)
            db.session.commit()

            AdminOperationLog.log_operation(
                admin_id=current_user.id,
                operation="add",
                entity_type="worker",
                entity_id=id_,
                details=f"Added worker: {name}"
            )
            
            flash('Worker added successfully.')
            return redirect(url_for('main.manage_workers'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: Worker ID already exists.')
        except ValueError:
            flash('Error: Invalid input for ID or other fields.')
    return render_template('admin/worker_form.html', action='Add')



@main.route('/admin/workers/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_worker(id):
    worker = Worker.query.get_or_404(id)
    workgroups = Workgroup.query.all()
    if request.method == 'POST':
        old_details = f"Name: {worker.name}, Type: {worker.type}, Initial Order: {worker.initial_order}"
        worker.name = request.form['name']
        worker.type = request.form['type']
        worker.initial_order = int(request.form['initial_order'])
        if 'password' in request.form and request.form['password']:
            worker.set_password(request.form['password'])
        db.session.commit()
        
        new_details = f"Name: {worker.name}, Type: {worker.type}, Initial Order: {worker.initial_order}"
        AdminOperationLog.log_operation(
            admin_id=current_user.id,
            operation="edit",
            entity_type="worker",
            entity_id=id,
            details=f"Changed from {old_details} to {new_details}"
        )
        
        flash('Worker updated successfully.')
        return redirect(url_for('main.manage_workers'))
    return render_template('admin/worker_form.html', action='Edit', worker=worker, workgroups=workgroups)




@main.route('/admin/workers/delete/<int:id>', methods=['POST'])
@admin_required
def delete_worker(id):
    worker = Worker.query.get_or_404(id)
    details = f"Name: {worker.name}, Type: {worker.type}, Initial Order: {worker.initial_order}"
    db.session.delete(worker)
    db.session.commit()
    
    AdminOperationLog.log_operation(
        admin_id=current_user.id,
        operation="delete",
        entity_type="worker",
        entity_id=id,
        details=f"Deleted worker: {details}"
    )
    
    flash('Worker deleted successfully.')
    return redirect(url_for('main.manage_workers'))

@main.route('/admin/workers/import', methods=['GET', 'POST'])
@admin_required
def import_workers():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded.')
            return redirect(url_for('main.import_workers'))
        file = request.files['file']
        if not file.filename:
            flash('No file selected.')
            return redirect(url_for('main.import_workers'))
        
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
                print(f"CSV DataFrame: {df}")  # Debug: Check CSV parsing
            elif file.filename.endswith('.xlsx'):
                # Specify header row for XLSX (assuming headers are in row 2, adjust if needed)
                df = pd.read_excel(file, header=1)
                print(f"XLSX DataFrame after header fix: {df}")  # Debug: Check XLSX parsing
            else:
                flash('Unsupported file type. Please upload a CSV or XLSX file.')
                return redirect(url_for('main.import_workers'))
            
            if df.empty:
                flash('The uploaded file is empty.')
                return redirect(url_for('main.import_workers'))
            
            # Ensure required columns are present
            required_columns = ['id', 'name','type', 'initial_order', 'password']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                flash(f'Missing required columns: {", ".join(missing_columns)}')
                return redirect(url_for('main.import_workers'))
            
            data = df.to_dict(orient='records')
            print(f"Data to preview: {data}")  # Debug: Verify final data
            session['worker_import_data'] = data
            return render_template('admin/worker_import_preview.html', data=data)
        except Exception as e:
            flash(f'Error reading file: {str(e)}')
            return redirect(url_for('main.import_workers'))
    return render_template('admin/worker_import.html')


@main.route('/admin/workers/import/confirm', methods=['POST'])
@admin_required
def confirm_import_workers():
    data = session.get('worker_import_data')
    if not data:
        flash('No import data found. Please upload a file again.')
        return redirect(url_for('main.import_workers'))
    
    workers = []
    errors = []
    # Pre-validate data
    existing_ids = {w.id for w in Worker.query.with_entities(Worker.id).all()}
    for row in data:
        try:
            worker_id = int(row['id'])
            if worker_id in existing_ids:
                errors.append(f"Worker ID {worker_id} already exists.")
                continue
            worker = Worker(
                id=worker_id,
                name=row['name'],
                role='worker',
                type=row['type'],
                initial_order=int(row['initial_order'])
            )
            worker.set_password(str(row['password']))
            workers.append(worker)
        except ValueError as e:
            errors.append(f"Invalid data for worker ID {row['id']}: {str(e)}")
        except Exception as e:
            errors.append(f"Error preparing worker ID {row['id']}: {str(e)}")
    
    if not errors and workers:
        try:
            db.session.add_all(workers)
            db.session.commit()
            for row in data:
                AdminOperationLog.log_operation(
                    admin_id=current_user.id,
                    operation="add",
                    entity_type="worker",
                    entity_id=row['id'],
                    details=f"Added worker: {row['name']}"
                )
        except Exception as e:
            db.session.rollback()
            errors.append(f"Database error: {str(e)}")
    
    session.pop('worker_import_data', None)
    
    if errors:
        return render_template('admin/worker_import_result.html', errors=errors, success=False)
    return render_template('admin/worker_import_result.html', success=True, errors=None)


# monitor the situation of registering the workgroup

@main.route('/admin/workgroup_registrations')
@admin_required
def workgroup_registrations():
    workgroups = Workgroup.query.all()
    registrations = {}
    for wg in workgroups:
        senior_count = WorkerSequence.query.filter_by(workgroup_id=wg.id, type='senior').count()
        junior_count = WorkerSequence.query.filter_by(workgroup_id=wg.id, type='junior').count()
        registrations[wg.id] = {
            'name': wg.name,
            'senior': senior_count,
            'junior': junior_count,
            'max_senior': wg.max_senior_workers,
            'max_junior': wg.max_junior_workers
        }
    
    # Query workers without a WorkerSequence
    workers_without_sequence = Worker.query.filter(
        not_(Worker.id.in_(db.session.query(WorkerSequence.worker_id).distinct()))
    ).all()
    
    return render_template('admin/workgroup_registrations.html', 
                           registrations=registrations, 
                           workers_without_sequence=workers_without_sequence)


@main.route('/admin/notify_unregistered_workers', methods=['POST'])
@admin_required
def notify_unregistered_workers():
    workers_without_sequence = Worker.query.filter(
        not_(Worker.id.in_(db.session.query(WorkerSequence.worker_id).distinct()))
    ).all()
    
    if not workers_without_sequence:
        flash('All workers have registered for a workgroup.')
        return redirect(url_for('main.workgroup_registrations'))
    
    for worker in workers_without_sequence:
        Notification.send_notification(
            recipient_id=worker.id,
            recipient_type='worker',
            message='Please register for a workgroup as soon as possible.'
        )
    
    flash(f'Notifications sent to {len(workers_without_sequence)} workers.')
    return redirect(url_for('main.workgroup_registrations'))


@main.route('/admin/publish_in_group_initial_order', methods=['POST'])
@admin_required
def publish_in_group_initial_order():
    # Get all workgroups
    workgroups = Workgroup.query.all()
    
    for wg in workgroups:
        for worker_type in ['senior', 'junior']:
            # Get sequences sorted by Worker's initial_order
            sequences = WorkerSequence.query.join(Worker).filter(
                WorkerSequence.workgroup_id == wg.id,
                WorkerSequence.type == worker_type,
                WorkerSequence.status =='initialized'
            ).order_by(asc(Worker.initial_order)).all()
            
            # Define weight factor based on worker type
            w = 1.5 if worker_type == 'senior' else 0.7
            # Set max_initial_order based on worker type
            max_initial_order = wg.max_senior_workers if worker_type == 'senior' else wg.max_junior_workers
            
            # Assign in_group_initial_order and calculate initial current_score
            for i, seq in enumerate(sequences, 1):
                seq.in_group_initial_order = i
                seq.sequence = i
                # Calculate base_points and current_score
                base_points = max_initial_order - i + 1
                seq.current_score = round(w * base_points,3)
                seq.status = 'pending'
    
    db.session.commit()
    
    # Notify workers with a sequence
    workers_with_sequence = Worker.query.join(WorkerSequence).all()
    for worker in workers_with_sequence:
        Notification.send_notification(
            recipient_id=worker.id,
            recipient_type='worker',
            message='Your in-group initial order has been published. You can now trade points for priority.'
        )
    
    flash('In-group initial orders published and notifications sent.')
    return redirect(url_for('main.workgroup_registrations'))




# confirm the final sequence, send notification and export the sequence


@main.route('/admin/confirm_sequence', methods=['POST'])
@admin_required
def confirm_sequence():
    # Step 1: Fetch and update pending sequences
    pending_sequences = WorkerSequence.query.filter_by(status='pending').all()

    if not pending_sequences:
        flash('No pending sequences to confirm.')
        return redirect(url_for('main.admin_dashboard'))
    
    # Step 2: Confirm sequences and send notifications
    for seq in pending_sequences:
        seq.status = 'confirmed'
        Notification.send_notification(
            recipient_id=seq.worker_id,
            recipient_type='worker',
            message=f'Your sequence in {seq.workgroup.name} ({seq.type}) is {seq.sequence}.'
        )
    db.session.commit()
    
    # Step 3: Prepare data for spreadsheet
    data = []
    workgroups = Workgroup.query.all()
    for wg in workgroups:
        for worker_type in ['senior', 'junior']:
            sequences = WorkerSequence.query.filter_by(
                workgroup_id=wg.id,
                type=worker_type,
                status='confirmed'
            ).order_by(WorkerSequence.sequence).all()
            for seq in sequences:
                data.append({
                    'Workgroup': wg.name,
                    'Type': worker_type,
                    'Worker ID': seq.worker_id,
                    'Worker Name': seq.worker_name,
                    'Sequence': seq.sequence,
                    'In-Group Initial Order': seq.in_group_initial_order,
                    'Current Score': seq.current_score
                })
    
    # Generate CSV
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    # Step 4: Log the operation
    AdminOperationLog.log_operation(
        admin_id=current_user.id,
        operation="confirm_sequence",
        entity_type="system",
        entity_id=None,
        details="Confirmed all pending sequences in the system and exported spreadsheet"
    )
    
    # Step 5: Send file for download
    return send_file(
        output,
        as_attachment=True,
        download_name='confirmed_sequences.csv',
        mimetype='text/csv'
    )

# export the sequence file


@main.route('/admin/export_schedule_by_worker', methods=['GET'])
@admin_required
def export_schedule_by_worker():
    # Fetch all workers
    workers = Worker.query.all()
    weekdays = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat', 7: 'Sun'}
    
    data = []
    for worker in workers:
        # Get the worker's sequence to find their workgroup
        sequence = WorkerSequence.query.filter_by(worker_id=worker.id).first()
        workgroup_name = sequence.workgroup.name if sequence and sequence.workgroup else 'None'
        name_with_workgroup = f"{worker.name}, ({workgroup_name})"
        
        # Format the worker's shifts
        shifts = [
            f"{schedule.shift.type}: {weekdays.get(schedule.shift.day, 'Unknown')} "
            f"{schedule.shift.start_time.strftime('%H:%M')}-{schedule.shift.end_time.strftime('%H:%M')}"
            for schedule in worker.schedules
        ]
        shifts_str = '\n'.join(shifts) if shifts else 'None'
        
        data.append({
            'Worker ID': worker.id,
            'Worker Name': name_with_workgroup,
            'Shifts': shifts_str
        })
    
    # Create CSV in memory
    si = StringIO()
    fieldnames = ['Worker ID', 'Worker Name', 'Shifts']
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
    
    # Stream the CSV as a response
    def generate():
        si.seek(0)
        yield si.read()
    
    return Response(
        generate(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=schedule_by_worker.csv"}
    )



@main.route('/admin/export_schedule_by_shift', methods=['GET'])
@admin_required
def export_schedule_by_shift():
    # Fetch all shifts
    shifts = Shift.query.all()
    weekdays = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat', 7: 'Sun'}
    
    data = []
    for shift in shifts:
        # List workers with their workgroup for this shift
        workers = []
        for schedule in shift.schedules:
            worker = schedule.worker
            # Get the worker's sequence to find their workgroup
            sequence = WorkerSequence.query.filter_by(worker_id=worker.id).first()
            workgroup_name = sequence.workgroup.name if sequence and sequence.workgroup else 'None'
            workers.append(f"{worker.name} ({workgroup_name})")
        
        workers_str = ', '.join(workers) if workers else 'None'
        
        data.append({
            'Shift ID': shift.id,
            'Shift Type': shift.type,
            'Day': weekdays.get(shift.day, 'Unknown'),
            'Start Time': shift.start_time.strftime('%H:%M'),
            'End Time': shift.end_time.strftime('%H:%M'),
            'Workers': workers_str
        })
    
    # Create CSV in memory
    si = StringIO()
    fieldnames = ['Shift ID', 'Shift Type', 'Day', 'Start Time', 'End Time', 'Workers']
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
    
    # Stream the CSV as a response
    def generate():
        si.seek(0)
        yield si.read()
    
    return Response(
        generate(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=schedule_by_shift.csv"}
    )




@main.route('/admin/reset_schedule', methods=['POST'])
@admin_required
def reset_schedule():
    # Delete all WorkerSequence entries
    WorkerSequence.query.delete()
    
    # Delete all Schedule entries
    Schedule.query.delete()
    
    # Delete all Notification entries
    Notification.query.delete()

    # Reset traded_points for all workers
    workers = Worker.query.all()
    for worker in workers:
        worker.traded_points = 0
        worker.points = worker.points  # Preserve earned points, or reset if desired
    
    # Commit the changes
    db.session.commit()

    # Log the reset operation
    AdminOperationLog.log_operation(
        admin_id=current_user.id,
        operation="reset_schedule",
        entity_type="system",
        entity_id=None,
        details="Deleted all previous WorkerSequence, Schedule, and Notification data, reset traded_points for all workers."
    )
    
    flash('Previous schedule information and notifications have been deleted. Ready for a new cycle.')
    return redirect(url_for('main.admin_dashboard'))



#---------------------------#





# workers
@main.route('/worker_dashboard')
@login_required
def worker_dashboard():
    if current_user.role != 'worker':
        flash('Access denied')
        return redirect(url_for('main.login'))
    
    can_choose = can_choose_schedule(current_user.id)
    unread_notifications = Notification.query.filter_by(
        recipient_id=current_user.id,
        recipient_type='worker'
    ).count()
    
    # Retrieve the worker's sequence and its status
    sequence = WorkerSequence.query.filter_by(worker_id=current_user.id).first()
    sequence_status = sequence.status if sequence else None
    
    return render_template('worker/worker_dashboard.html', 
                          can_choose_schedule=can_choose, 
                          unread_notifications=unread_notifications,
                          sequence_status=sequence_status)

def can_choose_schedule(worker_id):
    # Fetch the worker's sequence
    sequence = WorkerSequence.query.filter_by(worker_id=worker_id).first()
    
    # Check if sequence exists, status is 'confirmed', and sequence number is valid
    if not sequence or sequence.status != 'confirmed' or sequence.sequence is None:
        return False
    
    # Query prior workers with a lower sequence number
    prior_workers = WorkerSequence.query.filter(
        WorkerSequence.workgroup_id == sequence.workgroup_id,
        WorkerSequence.type == sequence.type,
        WorkerSequence.sequence < sequence.sequence
    ).all()
    
    # Check if all prior workers have at least one schedule
    for prior in prior_workers:
        if not Schedule.query.filter_by(worker_id=prior.worker_id).first():
            return False
    
    # Check if the current worker has not submitted any schedule yet
    if Schedule.query.filter_by(worker_id=worker_id).first():
        return False
    
    return True



@main.route('/worker/workgroup_selection', methods=['GET', 'POST'])
@login_required
def workgroup_selection():
    if current_user.role != 'worker':
        flash('Access denied.')
        return redirect(url_for('main.worker_dashboard'))
    
    worker_type = current_user.type  # 'senior' or 'junior'
    workgroups = Workgroup.query.all()
    
    # Calculate current worker counts per workgroup
    workgroup_counts = {}
    for wg in workgroups:
        count = WorkerSequence.query.filter_by(workgroup_id=wg.id, type=worker_type).count()
        max_allowed = wg.max_senior_workers if worker_type == 'senior' else wg.max_junior_workers
        workgroup_counts[wg.id] = {
            'count': count,
            'max': max_allowed,
            'full': count >= max_allowed
        }
    
    # Get the worker's current sequence
    sequence = WorkerSequence.query.filter_by(worker_id=current_user.id).first()
    
    # Determine if selection is allowed
    can_select = not sequence or sequence.status == 'initialized'
    
    # Handle form submission (POST request)
    if request.method == 'POST':
        if not can_select:
            flash('You cannot change your workgroup at this stage.')
            return redirect(url_for('main.workgroup_selection'))
        
        workgroup_id = int(request.form['workgroup_id'])
        workgroup = Workgroup.query.get(workgroup_id)
        if not workgroup:
            flash('Invalid workgroup selected.')
            return redirect(url_for('main.workgroup_selection'))
        
        # Check if the workgroup is full
        if workgroup_counts[workgroup_id]['full']:
            flash(f'This workgroup is already full for {worker_type} workers.')
            return redirect(url_for('main.workgroup_selection'))
        
        # Update or create worker sequence
        if sequence:
            sequence.workgroup_id = workgroup_id
            sequence.status = 'initialized'
        else:
            sequence = WorkerSequence(
                worker_id=current_user.id,
                type=current_user.type,
                workgroup_id=workgroup_id,
                status='initialized'
            )
        db.session.add(sequence)
        db.session.commit()
        flash('Workgroup chosen successfully.')
    
    # Render the template for GET requests
    return render_template('worker/workgroup_selection.html', 
                          workgroups=workgroups, 
                          workgroup_counts=workgroup_counts, 
                          sequence=sequence, 
                          can_select=can_select)




@main.route('/worker/priority_score_system', methods=['GET', 'POST'])
@login_required
def priority_score_system():
    if current_user.role != 'worker':
        flash('Access denied.')
        return redirect(url_for('main.worker_dashboard'))
    
    sequence = WorkerSequence.query.filter_by(worker_id=current_user.id).first()
    if not sequence:
        flash('Please select a workgroup first.')
        return redirect(url_for('main.workgroup_selection'))
    
    # Check if the sequence status is 'pending'
    if sequence.status != 'pending':
        flash('You cannot update your score at this time. The sequence is not in a pending state.', 'error')
        return redirect(url_for('main.worker_dashboard'))
    
    total_workers_in_group = WorkerSequence.query.filter_by(
        workgroup_id=sequence.workgroup_id,
        type=current_user.type
    ).count()
    
    # Define weights for seniors and juniors
    w_senior = 1.5  # Higher weight for seniors, not that huge increase 
    w_junior = 0.7  # Standard weight for juniors
    w = w_senior if current_user.type == 'senior' else w_junior
    
    if request.method == 'POST':
        if 'trade_points' in request.form:
            points = int(request.form['points'])
            if points <= current_user.points:
                current_user.points -= points
                current_user.traded_points = (current_user.traded_points or 0) + points
                db.session.commit()
                update_sequence(sequence.workgroup_id, current_user.type, w)
                flash('Points traded successfully.')
            else:
                flash('Not enough points.')
        elif 'withdraw_points' in request.form:
            points = int(request.form['withdraw_points'])
            if points <= current_user.traded_points:
                current_user.points += points
                current_user.traded_points -= points
                db.session.commit()
                update_sequence(sequence.workgroup_id, current_user.type, w)
                flash('Points withdrawn successfully.')
            else:
                flash('Not enough traded points to withdraw.')
        return redirect(url_for('main.priority_score_system'))
    
    return render_template('worker/priority_score_system.html', 
                           sequence=sequence, 
                           total_workers_in_group=total_workers_in_group)




def update_sequence(workgroup_id, worker_type, w):
    """Update sequence for all workers of the same type in the workgroup based on current_score."""
    # Fetch all sequences for the workgroup and worker type
    sequences = WorkerSequence.query.filter_by(workgroup_id=workgroup_id, type=worker_type).all()
    # Recalculate current_score for each worker
    for seq in sequences:
        seq.calculate_priority(w)
    # Sort by current_score (descending) and assign sequence numbers
    sorted_sequences = sorted(sequences, key=lambda s: s.current_score, reverse=True)
    for i, seq in enumerate(sorted_sequences, 1):
        seq.sequence = i
    db.session.commit()





@main.route('/worker/schedule_system', methods=['GET', 'POST'])
@login_required
def schedule_system():
    # Restrict access to workers only
    if current_user.role != 'worker':
        flash('Access denied', 'error')
        return redirect(url_for('main.worker_dashboard'))

    # Check if it's the worker's turn
    if not can_choose_schedule(current_user.id):
        flash('It is not your turn to choose schedules.', 'error')
        return redirect(url_for('main.worker_dashboard'))

    # Get worker's sequence details
    sequence = WorkerSequence.query.filter_by(worker_id=current_user.id).first()
    if not sequence:
        flash('No sequence found for you.', 'error')
        return redirect(url_for('main.worker_dashboard'))

    workgroup_id = sequence.workgroup_id
    worker_type = sequence.type

    # Fetch intervals for the workgroup and determine availability
    intervals = Interval.query.filter_by(workgroup_id=workgroup_id).all()
    for interval in intervals:
        interval.available = (interval.current_senior_workers < interval.max_senior_workers) if worker_type == 'senior' else (interval.current_junior_workers < interval.max_junior_workers)

    # Fetch available shifts based on interval availability
    # Start with all shifts linked to the workgroup via ShiftInterval
    shift_intervals = ShiftInterval.query.filter_by(workgroup_id=workgroup_id).join(Interval).all()
    available_shift_ids = set()
    
    for si in shift_intervals:
        interval = si.interval
        # If the interval is available for this worker type, include the shift
        if ((worker_type == 'senior' and interval.current_senior_workers < interval.max_senior_workers) or
            (worker_type == 'junior' and interval.current_junior_workers < interval.max_junior_workers)):
            available_shift_ids.add(si.shift_id)

    # Fetch only the available shifts
    shifts = Shift.query.filter(Shift.id.in_(available_shift_ids)).all() if available_shift_ids else []

    # Define weekdays list
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    if request.method == 'POST':
        selected_shift_ids = request.form.getlist('shifts')
        selected_shifts = []

        # Validate selected shifts
        for shift_id in selected_shift_ids:
            shift = Shift.query.get(int(shift_id))
            if not shift:
                flash(f'Invalid shift ID: {shift_id}', 'error')
                continue

            # Check for overlaps with already selected shifts (in this request)
            for existing_shift in selected_shifts:
                if (shift.day == existing_shift.day and
                    shift.start_time < existing_shift.end_time and
                    shift.end_time > existing_shift.start_time):
                    flash(f'Shift {shift.id} overlaps with another selected shift.', 'error')
                    return render_template('worker/schedule_system.html', intervals=intervals, shifts=shifts, weekdays=weekdays)

            # Check existing schedules for overlaps
            overlapping = Schedule.query.filter_by(worker_id=current_user.id).join(Shift).filter(
                Shift.day == shift.day,
                Shift.start_time < shift.end_time,
                Shift.end_time > shift.start_time
            ).first()
            if overlapping:
                flash(f'Shift {shift.id} overlaps with an existing schedule.', 'error')
                continue

            # Check interval availability using ShiftInterval
            shift_intervals = ShiftInterval.query.filter_by(shift_id=shift.id, workgroup_id=workgroup_id).all()
            for si in shift_intervals:
                interval = si.interval
                if worker_type == 'senior' and interval.current_senior_workers >= interval.max_senior_workers:
                    flash(f'Shift {shift.id} exceeds senior worker limit in interval {interval.id}.', 'error')
                    return render_template('worker/schedule_system.html', intervals=intervals, shifts=shifts, weekdays=weekdays)
                if worker_type == 'junior' and interval.current_junior_workers >= interval.max_junior_workers:
                    flash(f'Shift {shift.id} exceeds junior worker limit in interval {interval.id}.', 'error')
                    return render_template('worker/schedule_system.html', intervals=intervals, shifts=shifts, weekdays=weekdays)

            selected_shifts.append(shift)

        # Assign shifts, update intervals, and add points
        for shift in selected_shifts:
            new_schedule = Schedule(worker_id=current_user.id, shift_id=shift.id, workgroup_id=workgroup_id)
            db.session.add(new_schedule)
            # Update interval counts using ShiftInterval
            shift_intervals = ShiftInterval.query.filter_by(shift_id=shift.id, workgroup_id=workgroup_id).all()
            for si in shift_intervals:
                interval = si.interval
                if worker_type == 'senior':
                    interval.current_senior_workers += 1
                else:
                    interval.current_junior_workers += 1

        # Calculate and add points to the worker
        total_points = sum(shift.points for shift in selected_shifts)
        current_user.points += total_points

        # Commit all changes to the database
        db.session.commit()

        # Notify the next worker or admin
        next_worker = get_next_worker_in_sequence(sequence)
        if next_worker:
            Notification.send_notification(
                recipient_id=next_worker.id,
                recipient_type='worker',
                message='It is your turn to choose schedules.'
            )
        else:
            Notification.send_notification(
                recipient_id=111,  # Testing Admin ID, can be changed if implemented
                recipient_type='admin',
                message=f'All {worker_type} workers in {sequence.workgroup.name} have chosen their schedules.'
            )

        flash('Schedules submitted successfully!', 'success')
        return redirect(url_for('main.worker_dashboard'))

    # Pass weekdays to the template for GET request
    return render_template('worker/schedule_system.html', intervals=intervals, shifts=shifts, worker_type=worker_type, weekdays=weekdays)

def get_next_worker_in_sequence(current_sequence):
    next_sequence = WorkerSequence.query.filter_by(
        workgroup_id=current_sequence.workgroup_id,
        type=current_sequence.type,
        sequence=current_sequence.sequence + 1
    ).first()
    return next_sequence.worker if next_sequence else None





@main.route('/worker/schedule', methods=['GET'])
@login_required
def worker_schedule():
    # Check if the user is a worker
    if current_user.role != 'worker':
        flash('Access denied: Workers only.', 'error')
        return redirect(url_for('main.worker_dashboard'))  # Adjust redirect as needed
    
    # Query schedules for the current worker, joining with Shift
    schedules = Schedule.query.filter_by(worker_id=current_user.id).join(Shift).all()
    
    # Render the template with the schedules
    return render_template('worker/worker_schedule.html', schedules=schedules)


# notification system

@main.route('/notifications')
@login_required
def notifications():
    notifications = Notification.query.filter_by(
        recipient_id=current_user.id,
        recipient_type=current_user.role
    ).order_by(Notification.timestamp.desc()).all()
    return render_template('notifications.html', notifications=notifications)

@main.route('/notifications/read/<int:id>', methods=['POST'])
@login_required
def read_notification(id):
    notification = Notification.query.get_or_404(id)
    if notification.recipient_id == current_user.id and notification.recipient_type == current_user.role:
        notification.delete()
        flash('Notification marked as read and deleted.')
    else:
        flash('Unauthorized action.')
    return redirect(url_for('main.notifications'))