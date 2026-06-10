from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.db import connect_db

auth_controller = Blueprint('auth', __name__)

@auth_controller.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        raw_user_id = request.form.get('user_id') or request.form.get('emp_id') 
        password = request.form.get('password')

        if not raw_user_id or not password:
            flash('Please enter both User ID and Password.', 'error')
            return redirect(url_for('auth.login'))

        clean_id = str(raw_user_id).strip().upper()
        
        if not clean_id.startswith('EMP-'):
            flash('Invalid ID Format. Please use EMP-XXX (e.g., EMP-001)', 'error')
            return redirect(url_for('auth.login'))

        conn = connect_db()
        conn.row_factory = __import__('sqlite3').Row 
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.*, r."RoleName" 
            FROM "USERS" u 
            JOIN "ROLES" r ON u."RoleID" = r."RoleID" 
            WHERE u."UserID" = ? AND u."Password" = ? AND u."IsActive" = 1
        ''', (clean_id, password))
        
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user['UserID']
            session['full_name'] = f"{user['FirstName']} {user['LastName']}"
            session['role'] = user['RoleName']
            
            if user['RoleName'] == 'Admin':
                return redirect(url_for('admin.dashboard')) 
            else:
                return redirect(url_for('dashboard.index')) 
        else:
            flash('Invalid User ID or Password! Please try again.', 'error')
            
    return render_template('login.html')

@auth_controller.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('auth.login'))