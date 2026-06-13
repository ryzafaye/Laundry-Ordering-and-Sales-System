from flask import Blueprint, render_template, redirect, url_for, session, request
from models.db import connect_db

service_controller = Blueprint('service', __name__)

def is_logged_in():
    return 'user_id' in session

@service_controller.route('/services', methods=['GET'])
def services():
    if not is_logged_in(): return redirect(url_for('auth.login'))
    
    search_query = request.args.get('search', '').strip()
    
    conn = connect_db()
    cursor = conn.cursor()
    
    if search_query:
        cursor.execute('''
            SELECT * FROM "SERVICES" 
            WHERE "ServiceID" LIKE ? 
               OR "ServiceName" LIKE ? 
               OR "Description" LIKE ?
            ORDER BY "ServiceID" ASC
        ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute('SELECT * FROM "SERVICES" ORDER BY "ServiceID" ASC')
        
    all_services = cursor.fetchall()
    conn.close()
    
    return render_template('services.html', services=all_services, current_search=search_query)