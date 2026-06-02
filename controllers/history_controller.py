from flask import Blueprint, render_template, redirect, url_for, session
from models.db import connect_db

history_controller = Blueprint('history', __name__)

@history_controller.route('/history')
def transaction_history():
    if 'emp_id' not in session:
        return redirect(url_for('auth.login'))
        
    conn = connect_db()
    conn.row_factory = None
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            p."PaymentID", 
            o."OrderID", 
            c."FirstName", c."LastName", 
            o."OrderDate", 
            o."ClaimedDate", 
            p."PaymentMethod", 
            o."OrderStatus",
            p."AmountPaid",
            (SELECT GROUP_CONCAT(s."ServiceName" || ' (' || od."WeightQuantity" || ')', '<br>') 
             FROM "ORDER_DETAILS" od 
             JOIN "SERVICES" s ON od."ServiceID" = s."ServiceID" 
             WHERE od."OrderID" = o."OrderID") AS ServiceNames
        FROM "PAYMENTS" p
        JOIN "ORDERS" o ON p."OrderID" = o."OrderID"
        JOIN "CUSTOMERS" c ON o."CustomerID" = c."CustomerID"
        ORDER BY o."OrderDate" DESC
    """)
    
    records_data = cursor.fetchall()
    conn.close()
    
    formatted_records = []
    for row in records_data:
        status_display = 'Cancelled' if row[7] == 'Cancelled' else 'Paid'
        
        formatted_records.append({
            'PaymentID': row[0],
            'OrderID': row[1],
            'CustomerName': f"{row[2]} {row[3]}",
            'OrderDate': row[4],
            'ClaimedDate': row[5] if row[5] else '---',
            'PaymentMethod': row[6],
            'Status': status_display,
            'AmountPaid': row[8],
            'ServiceNames': row[9] if row[9] else 'N/A'
        })
    
    return render_template('history.html', records=formatted_records)