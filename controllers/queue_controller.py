from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
from models.db import connect_db
from datetime import datetime
import json 

queue_controller = Blueprint('queue', __name__)

def is_logged_in():
    return 'emp_id' in session

@queue_controller.route('/queue')
def active_orders():
    if not is_logged_in():
        return redirect(url_for('auth.login'))
        
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o."OrderID", o."CustomerID", c."FirstName", c."LastName", 
               o."OrderDate", o."ClaimingMethod", o."OrderStatus", o."TotalAmount"
        FROM "ORDERS" o
        JOIN "CUSTOMERS" c ON o."CustomerID" = c."CustomerID"
        ORDER BY o."OrderDate" DESC
    """)
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
            'OrderStatus': row[6],
            'TotalAmount': row[7],
            'items_json': json.dumps(items)  
        })
    
    return render_template('queue.html', orders=formatted_orders)

@queue_controller.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    if not is_logged_in():
        return redirect(url_for('auth.login'))
        
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE "ORDERS" SET "OrderStatus" = \'Cancelled\' WHERE "OrderID" = ? AND "OrderStatus" = \'Pending\'', (order_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('queue.active_orders'))

@queue_controller.route('/update_status/<int:order_id>', methods=['POST'])
def update_status(order_id):
    if not is_logged_in():
        return jsonify({'success': False})
        
    new_status = request.form.get('status')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    if new_status == 'Claimed':
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('UPDATE "ORDERS" SET "OrderStatus" = ?, "ClaimedDate" = ? WHERE "OrderID" = ?', (new_status, current_time, order_id))
    else:
        cursor.execute('UPDATE "ORDERS" SET "OrderStatus" = ? WHERE "OrderID" = ?', (new_status, order_id))
        
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})