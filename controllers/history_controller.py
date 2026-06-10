from flask import Blueprint, render_template, redirect, url_for, session, request
from models.db import connect_db

history_controller = Blueprint('history', __name__)

@history_controller.route('/history', methods=['GET'])
def transaction_history():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')
    date_filter = request.args.get('date', '')
        
    conn = connect_db()
    conn.row_factory = None
    cursor = conn.cursor()
    
    base_sql = """
        SELECT 
            o."OrderID", 
            c."FirstName", c."LastName", 
            o."OrderDate", 
            o."ClaimedDate", 
            p."PaymentMethod", 
            o."StatusID",
            p."AmountPaid",
            (SELECT GROUP_CONCAT(s."ServiceName" || ' (' || od."WeightQuantity" || ')', '<br>') 
             FROM "ORDER_DETAILS" od 
             JOIN "SERVICES" s ON od."ServiceID" = s."ServiceID" 
             WHERE od."OrderID" = o."OrderID") AS ServiceNames
        FROM "PAYMENTS" p
        JOIN "ORDERS" o ON p."OrderID" = o."OrderID"
        JOIN "CUSTOMERS" c ON o."CustomerID" = c."CustomerID"
        WHERE 1=1
    """
    params = []
    
    if status_filter == 'paid':
        base_sql += " AND o.\"StatusID\" != 'S-05'"
    elif status_filter == 'cancelled':
        base_sql += " AND o.\"StatusID\" = 'S-05'"
        
    if date_filter:
        base_sql += " AND o.\"OrderDate\" LIKE ?"
        params.append(f"{date_filter}%")
        
    if search_query:
        base_sql += ' AND (o."OrderID" LIKE ? OR c."FirstName" LIKE ? OR c."LastName" LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])
        
    base_sql += ' ORDER BY o."OrderDate" DESC'
    
    cursor.execute(base_sql, params)
    records_data = cursor.fetchall()
    conn.close()
    
    formatted_records = []
    for row in records_data:
        status_display = 'Cancelled' if row[6] == 'S-05' else 'Paid'
        
        formatted_records.append({
            'OrderID': row[0],
            'CustomerName': f"{row[1]} {row[2]}",
            'OrderDate': row[3],
            'ClaimedDate': row[4] if row[4] else '---',
            'PaymentMethod': row[5],
            'Status': status_display,
            'AmountPaid': row[7],
            'ServiceNames': row[8] if row[8] else 'N/A'
        })
    
    return render_template('history.html', 
                           records=formatted_records, 
                           current_search=search_query, 
                           current_status=status_filter, 
                           current_date=date_filter)