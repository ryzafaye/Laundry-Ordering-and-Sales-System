from flask import Blueprint, render_template, redirect, url_for, session
from models.db import connect_db
from datetime import datetime

dashboard_controller = Blueprint('dashboard', __name__)

@dashboard_controller.route('/dashboard')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    conn = connect_db()
    conn.row_factory = None
    cursor = conn.cursor()
    
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('SELECT SUM("AmountPaid") FROM "PAYMENTS" WHERE "PaymentDate" LIKE ?', (today_date + '%',))
    today_sales = cursor.fetchone()[0] or 0.0
    
    cursor.execute('SELECT COUNT(*) FROM "ORDERS" WHERE "StatusID" = \'S-02\'')
    washing_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM "ORDERS" WHERE "StatusID" = \'S-03\' AND "ClaimingMethod" = \'Pickup\'')
    pickup_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM "ORDERS" WHERE "StatusID" IN (\'S-01\', \'S-02\', \'S-03\') AND "ClaimingMethod" = \'Delivery\'')
    delivery_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM "ORDERS" WHERE "StatusID" = \'S-04\'')
    completed_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM("AmountPaid") FROM "PAYMENTS" WHERE "PaymentMethod" = \'Cash\' AND "PaymentDate" LIKE ?', (today_date + '%',))
    cash_sales = cursor.fetchone()[0] or 0.0
    
    cursor.execute('SELECT SUM("AmountPaid") FROM "PAYMENTS" WHERE "PaymentMethod" != \'Cash\' AND "PaymentDate" LIKE ?', (today_date + '%',))
    online_sales = cursor.fetchone()[0] or 0.0
    
    cursor.execute('''
        SELECT 
            o."OrderID", c."FirstName", c."LastName", o."TotalAmount", 
            p."PaymentMethod", os."StatusName",
            (SELECT GROUP_CONCAT(s."ServiceName", ', ') FROM "ORDER_DETAILS" od JOIN "SERVICES" s ON od."ServiceID" = s."ServiceID" WHERE od."OrderID" = o."OrderID")
        FROM "ORDERS" o
        JOIN "CUSTOMERS" c ON o."CustomerID" = c."CustomerID"
        JOIN "ORDER_STATUS" os ON o."StatusID" = os."StatusID"
        LEFT JOIN "PAYMENTS" p ON o."OrderID" = p."OrderID"
        WHERE o."StatusID" NOT IN ('S-04', 'S-05')
        ORDER BY o."OrderDate" DESC LIMIT 10
    ''')
    recent_data = cursor.fetchall()
    
    recent_orders = []
    for row in recent_data:
        recent_orders.append({
            'OrderID': row[0],
            'CustomerName': f"{row[1]} {row[2]}",
            'TotalAmount': row[3],
            'PaymentMethod': row[4] if row[4] else 'N/A',
            'OrderStatus': row[5],
            'Services': row[6] if row[6] else 'N/A'
        })
        
    conn.close()
    
    return render_template('dashboard.html', 
                           today_sales=today_sales,
                           washing_count=washing_count,
                           pickup_count=pickup_count,
                           delivery_count=delivery_count,
                           completed_count=completed_count,
                           cash_sales=cash_sales,
                           online_sales=online_sales,
                           recent_orders=recent_orders)