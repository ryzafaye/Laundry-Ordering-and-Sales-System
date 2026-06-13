from flask import Blueprint, render_template, redirect, url_for, session, request, flash
import json
from models.db import connect_db
from datetime import datetime, timedelta, timezone

order_controller = Blueprint('order', __name__)

def is_logged_in():
    return 'user_id' in session

@order_controller.route('/order')
def pos():
    if not is_logged_in():
        return redirect(url_for('auth.login'))
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM "CUSTOMERS" 
        ORDER BY "FirstName" ASC
    ''')
    all_customers = cursor.fetchall()
    
    cursor.execute('''
        SELECT * FROM "SERVICES" 
        ORDER BY "ServiceID" ASC
    ''')
    all_services = cursor.fetchall()
    
    conn.close()
    
    return render_template('order.html', customers=all_customers, services=all_services)

@order_controller.route('/save_order', methods=['POST'])
def save_order():
    if not is_logged_in():
        return redirect(url_for('auth.login'))
    
    customer_id = request.form.get('customer_id')
    claiming_method = request.form.get('fulfillment')
    payment_method = request.form.get('payment_method')
    amount_tendered = request.form.get('amount_tendered')
    basket_data_json = request.form.get('basket_data')
    
    user_id = session.get('user_id')
    if not user_id:
        user_id = None 

    conn = connect_db()
    cursor = conn.cursor()

    try:
        basket_items = json.loads(basket_data_json)
        
        total_amount = sum(float(item['subtotal']) for item in basket_items)
        if claiming_method == 'Delivery':
            total_amount += 60.00
            
        PHT = timezone(timedelta(hours=8))
        ph_time = datetime.now(PHT).strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('SELECT "OrderID" FROM "ORDERS" ORDER BY "OrderID" DESC LIMIT 1')
        last_record = cursor.fetchone()
        
        if last_record:
            last_number = int(last_record[0].split('-')[1])
            new_order_id = f"ORD-{last_number + 1:03d}"
        else:
            new_order_id = "ORD-001"
            
        cursor.execute('''
            INSERT INTO "ORDERS" 
            ("OrderID", "CustomerID", "ProcessedByUserID", "ClaimingMethod", "StatusID", "TotalAmount", "OrderDate")
            VALUES (?, ?, ?, ?, 'S-01', ?, ?)
        ''', (new_order_id, customer_id, user_id, claiming_method, total_amount, ph_time))
        
        for item in basket_items:
            cursor.execute('''
                INSERT INTO "ORDER_DETAILS" 
                ("OrderID", "ServiceID", "WeightQuantity", "ServicePrice", "Subtotal")
                VALUES (?, ?, ?, ?, ?)
            ''', (new_order_id, item['service_id'], item['qty'], item['rate'], item['subtotal']))
        
        if amount_tendered and amount_tendered.strip() != "":
            actual_paid = float(amount_tendered)
        else:
            actual_paid = total_amount
            
        cursor.execute('''
            INSERT INTO "PAYMENTS" 
            ("OrderID", "PaymentMethod", "AmountPaid", "PaymentDate")
            VALUES (?, ?, ?, ?)
        ''', (new_order_id, payment_method, actual_paid, ph_time))
        
        conn.commit()
        
    except Exception as e:
        print(f"DATABASE ERROR: {e}")
        
    finally:
        conn.close()
        
    return redirect(url_for('order.pos'))

@order_controller.route('/cancel_order/<string:order_id>', methods=['POST'])
def cancel_order(order_id):
    if not is_logged_in():
        return redirect(url_for('auth.login'))
        
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE "ORDERS" 
            SET "StatusID" = 'S-05' 
            WHERE "OrderID" = ?
        ''', (order_id,))
                
        conn.commit()
        flash(f"Order {order_id} has been successfully cancelled.", "success")
        
    except Exception as e:
        print(f"DATABASE ERROR: {e}")
        flash("Failed to cancel the order due to a system error.", "error")
        
    finally:
        conn.close()
        
    return redirect(request.referrer or url_for('order.pos'))