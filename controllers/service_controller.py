from flask import Blueprint, render_template, redirect, url_for, session
from models.db import connect_db

service_controller = Blueprint('service', __name__)

def is_logged_in():
    return 'emp_id' in session

@service_controller.route('/services')
def services():
    if not is_logged_in(): return redirect(url_for('auth.login'))
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM "SERVICES" ORDER BY "ServiceID" ASC')
    all_services = cursor.fetchall()
    conn.close()
    
    return render_template('services.html', services=all_services)