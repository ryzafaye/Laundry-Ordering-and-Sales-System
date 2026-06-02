from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.db import connect_db

auth_controller = Blueprint('auth', __name__)

@auth_controller.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        raw_emp_id = request.form.get('emp_id') 
        password = request.form.get('password')

        clean_id = raw_emp_id.upper().replace('EMP-', '').replace('ADM-', '')
        
        try:
            emp_id = int(clean_id) 
        except ValueError:
            flash('Invalid ID Format. Please use EMP-XXX or ADM-XXX', 'error')
            return redirect(url_for('auth.login'))

        conn = connect_db()
        conn.row_factory = __import__('sqlite3').Row 
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM "EMPLOYEES" WHERE "EmpID" = ? AND "Password" = ?', (emp_id, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['emp_id'] = user['EmpID']
            session['full_name'] = f"{user['FirstName']} {user['LastName']}"
            session['position'] = user['Position']
            
            if user['Position'] == 'Admin':
                return redirect(url_for('admin.dashboard')) 
            else:
                return redirect(url_for('dashboard.index')) 
        else:
            flash('Invalid Employee ID or Password!', 'error')
            
    return render_template('login.html')

@auth_controller.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('auth.login'))