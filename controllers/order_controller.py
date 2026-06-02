from flask import Blueprint, render_template, redirect, url_for, session, request, flash
import json
from models.db import connect_db

order_controller = Blueprint('order', __name__)

def is_logged_in():
    return 'emp_id' in session

@order_controller.route('/order')
def pos():
    if not is_logged_in():
        return redirect(url_for('auth.login'))
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT "CustomerID", "FirstName", "LastName" FROM "CUSTOMERS" ORDER BY "FirstName" ASC')
    all_customers = cursor.fetchall()
    
    cursor.execute('SELECT * FROM "CUSTOMERS" ORDER BY "FirstName" ASC')
    all_customers = cursor.fetchall()
    
    cursor.execute('SELECT * FROM "SERVICES" ORDER BY "ServiceID" ASC')
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
    
    emp_id = session.get('emp_id')
    if not emp_id:
        emp_id = None 

    conn = connect_db()
    cursor = conn.cursor()

    try:
        basket_items = json.loads(basket_data_json)
        
        total_amount = sum(float(item['subtotal']) for item in basket_items)
        if claiming_method == 'Delivery':
            total_amount += 60.00
            
        cursor.execute("""
            INSERT INTO "ORDERS" 
            ("CustomerID", "ProcessedByEmpID", "ClaimingMethod", "OrderStatus", "TotalAmount")
            VALUES (?, ?, ?, 'Pending', ?)
        """, (customer_id, emp_id, claiming_method, total_amount))
        
        order_id = cursor.lastrowid
        
        for item in basket_items:
            cursor.execute("""
                INSERT INTO "ORDER_DETAILS" 
                ("OrderID", "ServiceID", "WeightQuantity", "ServicePrice", "Subtotal")
                VALUES (?, ?, ?, ?, ?)
            """, (order_id, item['service_id'], item['qty'], item['rate'], item['subtotal']))
        
        if amount_tendered and amount_tendered.strip() != "":
            actual_paid = float(amount_tendered)
        else:
            actual_paid = total_amount
            
        cursor.execute("""
            INSERT INTO "PAYMENTS" 
            ("OrderID", "PaymentMethod", "PaymentStatus", "AmountPaid")
            VALUES (?, ?, 'Paid', ?)
        """, (order_id, payment_method, actual_paid))
        
        conn.commit()
        print(f"SUCCESS: Order #{order_id} has been saved to the database!")
        
    except Exception as e:
        print(f"DATABASE ERROR: {e}")
        
    finally:
        conn.close()
        
    return redirect(url_for('order.pos'))

@order_controller.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    if not is_logged_in():
        return redirect(url_for('auth.login'))
        
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE "ORDERS" 
            SET "OrderStatus" = 'Cancelled' 
            WHERE "OrderID" = ?
        ''', (order_id,))
        
        cursor.execute('''
            UPDATE "PAYMENTS" 
            SET "PaymentStatus" = 'Voided' 
            WHERE "OrderID" = ?
        ''', (order_id,))
        
        conn.commit()
        flash(f"Order #{order_id} has been successfully cancelled and payment is voided.", "success")
        print(f"SUCCESS: Order #{order_id} cancelled.")
        
    except Exception as e:
        print(f"DATABASE ERROR CANCELLING ORDER: {e}")
        flash("Failed to cancel the order due to a system error.", "error")
        
    finally:
        conn.close()
        
    return redirect(request.referrer or url_for('order.pos'))