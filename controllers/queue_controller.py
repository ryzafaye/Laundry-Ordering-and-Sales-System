from flask import Blueprint, render_template, redirect, url_for, session, request
from models.db import connect_db
from datetime import datetime, timedelta, timezone
import json 

queue_controller = Blueprint('queue', __name__)

def is_logged_in():
    return 'user_id' in session

@queue_controller.route('/queue', methods=['GET'])
def active_orders():
    if not is_logged_in():
        return redirect(url_for('auth.login'))
        
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'active')
        
    conn = connect_db()
    cursor = conn.cursor()
    
    base_sql = """
        SELECT o."OrderID", o."CustomerID", c."FirstName", c."LastName", 
               o."OrderDate", o."ClaimingMethod", o."StatusID", os."StatusName", o."TotalAmount"
        FROM "ORDERS" o
        JOIN "CUSTOMERS" c ON o."CustomerID" = c."CustomerID"
        JOIN "ORDER_STATUS" os ON o."StatusID" = os."StatusID"
        WHERE 1=1
    """
    params = []
    
    if status_filter == 'active':
        base_sql += " AND o.\"StatusID\" NOT IN ('S-04', 'S-05')" 
    elif status_filter != 'all':
        base_sql += " AND o.\"StatusID\" = ?"
        params.append(status_filter)
        
    if search_query:
        base_sql += ' AND (o."OrderID" LIKE ? OR c."FirstName" LIKE ? OR c."LastName" LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])
        
    base_sql += ' ORDER BY o."OrderDate" DESC'
    
    cursor.execute(base_sql, params)
    orders_data = cursor.fetchall()
    
    cursor.execute("""
        SELECT od."OrderID", s."ServiceName", od."WeightQuantity", od."Subtotal"
        FROM "ORDER_DETAILS" od
        JOIN "SERVICES" s ON od."ServiceID" = s."ServiceID"
    """)
    details_data = cursor.fetchall()
    conn.close()
    
    details_dict = {}
    for row in details_data:
        o_id = row[0]
        if o_id not in details_dict:
            details_dict[o_id] = []
        details_dict[o_id].append({
            'service': row[1],
            'qty': float(row[2]),
            'subtotal': float(row[3])
        })
    
    formatted_orders = []
    for row in orders_data:
        o_id = row[0]
        items = details_dict.get(o_id, [])
        formatted_orders.append({
            'OrderID': o_id,
            'CustomerID': row[1],
            'FirstName': row[2],
            'LastName': row[3],
            'OrderDate': row[4],
            'ClaimingMethod': row[5],
            'StatusID': row[6],
            'StatusName': row[7],
            'TotalAmount': row[8],
            'items_json': json.dumps(items)  
        })
    
    return render_template('queue.html', orders=formatted_orders, current_search=search_query, current_status=status_filter)

@queue_controller.route('/cancel_order/<string:order_id>', methods=['POST'])
def cancel_order(order_id):
    if not is_logged_in():
        return redirect(url_for('auth.login'))
        
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE "ORDERS" SET "StatusID" = \'S-05\' WHERE "OrderID" = ?', (order_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('queue.active_orders'))

@queue_controller.route('/update_status/<string:order_id>', methods=['POST'])
def update_status(order_id):
    if not is_logged_in():
        return redirect(url_for('auth.login'))
        
    new_status_id = request.form.get('status_id') or request.form.get('status')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    if new_status_id == 'S-04':
        PHT = timezone(timedelta(hours=8))
        ph_time = datetime.now(PHT).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('UPDATE "ORDERS" SET "StatusID" = ?, "ClaimedDate" = ? WHERE "OrderID" = ?', (new_status_id, ph_time, order_id))
    else:
        cursor.execute('UPDATE "ORDERS" SET "StatusID" = ? WHERE "OrderID" = ?', (new_status_id, order_id))
        
    conn.commit()
    conn.close()
    
    return redirect(url_for('queue.active_orders'))