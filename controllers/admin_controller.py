from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from models.db import connect_db
import sqlite3
import json

admin_controller = Blueprint('admin', __name__, url_prefix='/admin')

def is_admin():
    return 'emp_id' in session and session.get('position') == 'Admin'

@admin_controller.route('/dashboard')
def dashboard():
    if not is_admin():
        return redirect(url_for('auth.login'))

    conn = connect_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT SUM("AmountPaid") 
        FROM "PAYMENTS" 
        WHERE "PaymentStatus" = 'Paid' 
        AND strftime('%m', "PaymentDate") = strftime('%m', 'now', '+8 hours') 
        AND strftime('%Y', "PaymentDate") = strftime('%Y', 'now', '+8 hours')
    ''')
    res = cursor.fetchone()
    monthly_revenue = res[0] if (res and res[0] is not None) else 0.0

    cursor.execute('''
        SELECT COUNT(*) 
        FROM "EMPLOYEES" 
        WHERE "Position" != 'Admin'
    ''')
    res = cursor.fetchone()
    staff_count = res[0] if (res and res[0] is not None) else 0

    cursor.execute('''
        SELECT COUNT(*) 
        FROM "ORDERS" 
        WHERE date("OrderDate") = date('now', '+8 hours')
    ''')
    res = cursor.fetchone()
    orders_today = res[0] if (res and res[0] is not None) else 0

    cursor.execute('''
        SELECT COUNT(*) 
        FROM "CUSTOMERS"
    ''')
    res = cursor.fetchone()
    customer_count = res[0] if (res and res[0] is not None) else 0

    cursor.execute('''
        SELECT SUM("AmountPaid") 
        FROM "PAYMENTS" 
        WHERE "PaymentStatus" = 'Paid' 
        AND date("PaymentDate") = date('now', '+8 hours')
    ''')
    res = cursor.fetchone()
    income_today = res[0] if (res and res[0] is not None) else 0.0

    cursor.execute('''
        SELECT SUM(o."TotalAmount") 
        FROM "ORDERS" o
        LEFT JOIN "PAYMENTS" p ON o."OrderID" = p."OrderID"
        WHERE o."OrderStatus" != 'Cancelled' AND (p."PaymentStatus" IS NULL OR p."PaymentStatus" != 'Paid')
    ''')
    res = cursor.fetchone()
    pending_collectibles = res[0] if (res and res[0] is not None) else 0.0

    cursor.execute('''
        SELECT COUNT(*) 
        FROM "ORDERS" 
        WHERE "OrderStatus" = 'Claimed'
    ''')
    res = cursor.fetchone()
    completed_orders = res[0] if (res and res[0] is not None) else 0

    cursor.execute('''
        SELECT 
            o."OrderID", 
            c."FirstName" || ' ' || c."LastName" AS CustomerName,
            e."FirstName" AS StaffName, 
            o."TotalAmount", 
            CASE 
                WHEN o."OrderStatus" = 'Cancelled' THEN 'Voided'
                ELSE IFNULL(p."PaymentStatus", 'Unpaid') 
            END AS PaymentStatus, 
            o."OrderStatus"
        FROM "ORDERS" o
        JOIN "CUSTOMERS" c ON o."CustomerID" = c."CustomerID"
        LEFT JOIN "EMPLOYEES" e ON o."ProcessedByEmpID" = e."EmpID"
        LEFT JOIN "PAYMENTS" p ON o."OrderID" = p."OrderID"
        ORDER BY o."OrderDate" DESC 
        LIMIT 10
    ''')

    recent_orders = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return render_template('admin-dashboard.html', 
                           monthly_revenue=monthly_revenue,
                           staff_count=staff_count,
                           orders_today=orders_today,
                           customer_count=customer_count,
                           income_today=income_today,
                           pending_collectibles=pending_collectibles,
                           completed_orders=completed_orders,
                           recent_orders=recent_orders)

@admin_controller.route('/staff')
def staff_management():
    if not is_admin():
        return redirect(url_for('auth.login'))
        
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM "EMPLOYEES" 
        WHERE "Status" = 'Active' OR "Status" IS NULL
    ''')   
    employees = cursor.fetchall()
    
    total_emp = len(employees)
    admin_count = sum(1 for emp in employees if emp['Position'] == 'Admin')
    staff_count = total_emp - admin_count
    
    conn.close()
    
    return render_template('admin-staff.html', 
                           employees=employees, 
                           total_emp=total_emp, 
                           admin_count=admin_count,
                           staff_count=staff_count)

@admin_controller.route('/staff/add', methods=['POST'])
def add_staff():
    if not is_admin(): return redirect(url_for('auth.login'))
    
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    role = request.form.get('role')
    password = request.form.get('password')
    contact = request.form.get('contact')
    
    if len(contact) != 11 or not contact.startswith('09') or not contact.isdigit():
        flash("Invalid contact number! It must be 11 digits and start with '09'.", "error")
        return redirect(url_for('admin.staff_management'))
    
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO "EMPLOYEES" ("FirstName", "LastName", "Position", "Password", "ContactNumber", "Status")
            VALUES (?, ?, ?, ?, ?, 'Active')
        ''', (fname, lname, role, password, contact))
        conn.commit()
        flash("New employee added successfully!", "success")
    except Exception as e:
        flash(f"Error saving to database: {e}", "error")
    finally:
        conn.close()
        
    return redirect(url_for('admin.staff_management'))

@admin_controller.route('/staff/edit/<int:emp_id>', methods=['POST'])
def edit_staff(emp_id):
    if not is_admin(): return redirect(url_for('auth.login'))
    
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    role = request.form.get('role')
    contact = request.form.get('contact')
    new_password = request.form.get('new_password') 
    
    if len(contact) != 11 or not contact.startswith('09') or not contact.isdigit():
        flash("Invalid contact number! It must be 11 digits and start with '09'.", "error")
        return redirect(url_for('admin.staff_management'))
    
    conn = connect_db()
    cursor = conn.cursor()
    try:
        if new_password and new_password.strip() != "":
            cursor.execute('''
                UPDATE "EMPLOYEES" 
                SET "FirstName" = ?, "LastName" = ?, "Position" = ?, "ContactNumber" = ?, "Password" = ?
                WHERE "EmpID" = ?
            ''', (fname, lname, role, contact, new_password, emp_id))
            flash("Employee record and password updated!", "success")
        else:
            cursor.execute('''
                UPDATE "EMPLOYEES" 
                SET "FirstName" = ?, "LastName" = ?, "Position" = ?, "ContactNumber" = ?
                WHERE "EmpID" = ?
            ''', (fname, lname, role, contact, emp_id))
            flash("Employee record updated!", "success")
            
        conn.commit()
    except Exception as e:
        flash(f"Error updating database: {e}", "error")
    finally:
        conn.close()
    
    return redirect(url_for('admin.staff_management'))

@admin_controller.route('/staff/delete/<int:emp_id>', methods=['POST'])
def delete_staff(emp_id):
    if not is_admin(): return redirect(url_for('auth.login'))
    
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE "EMPLOYEES" 
            SET "Status" = 'Inactive' 
            WHERE "EmpID" = ?
        ''', (emp_id,))
        conn.commit()
    except Exception as e:
        print(f"Cannot delete: {e}")
    finally:
        conn.close()
        
    return redirect(url_for('admin.staff_management'))

@admin_controller.route('/orders')
def all_orders():
    if not is_admin():
        return redirect(url_for('auth.login'))
        
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            o."OrderID", o."OrderDate", o."ClaimedDate", o."TotalAmount", o."OrderStatus", o."ProcessedByEmpID",
            c."FirstName" AS CustFirstName, c."LastName" AS CustLastName, c."CustomerID",
            p."PaymentStatus", p."PaymentMethod",
            e."FirstName" AS EmpFirstName, e."LastName" AS EmpLastName
        FROM "ORDERS" o
        LEFT JOIN "CUSTOMERS" c ON o."CustomerID" = c."CustomerID"
        LEFT JOIN "PAYMENTS" p ON o."OrderID" = p."OrderID"
        LEFT JOIN "EMPLOYEES" e ON o."ProcessedByEmpID" = e."EmpID"
        ORDER BY o."OrderDate" DESC
    ''')
    
    orders_data = cursor.fetchall()
    
    all_orders_list = []
    for row in orders_data:
        order_dict = dict(row)
        
        cursor.execute('''
            SELECT s."ServiceName", od."WeightQuantity", od."Subtotal"
            FROM "ORDER_DETAILS" od
            JOIN "SERVICES" s ON od."ServiceID" = s."ServiceID"
            WHERE od."OrderID" = ?
        ''', (row['OrderID'],))
        services_data = cursor.fetchall()
        
        services_list = []
        for s in services_data:
            services_list.append({
                'name': s['ServiceName'],
                'qty': s['WeightQuantity'],
                'subtotal': s['Subtotal']
            })
        
        order_dict['ServicesJSON'] = json.dumps(services_list)
        
        all_orders_list.append(order_dict)

    conn.close()
    
    return render_template('admin-order.html', orders=all_orders_list)

@admin_controller.route('/reports', methods=['GET', 'POST'])
def financial_reports():
    if not is_admin():
        return redirect(url_for('auth.login'))
        
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    where_o = "WHERE 1=1"
    where_p = "WHERE p.\"PaymentStatus\" = 'Paid'"
    where_c = "WHERE 1=1"
    params_o, params_p, params_c = [], [], []

    if start_date and end_date:
        where_o += " AND date(o.\"OrderDate\") BETWEEN ? AND ?"
        where_p += " AND date(p.\"PaymentDate\") BETWEEN ? AND ?"
        where_c += " AND date(\"DateRegistered\") BETWEEN ? AND ?"
        params_o.extend([start_date, end_date])
        params_p.extend([start_date, end_date])
        params_c.extend([start_date, end_date])

    cursor.execute(f'''SELECT SUM("AmountPaid") FROM "PAYMENTS" p {where_p}''', params_p)
    total_sales = cursor.fetchone()[0] or 0.0

    cursor.execute(f'''SELECT COUNT(*) FROM "ORDERS" o {where_o}''', params_o)
    total_orders = cursor.fetchone()[0] or 0

    cursor.execute(f'''SELECT COUNT(*) FROM "CUSTOMERS" {where_c}''', params_c)
    total_customers = cursor.fetchone()[0] or 0

    cursor.execute(f'''SELECT COUNT(*) FROM "PAYMENTS" p {where_p}''', params_p)
    total_payments = cursor.fetchone()[0] or 0
    
    avg_order_value = (total_sales / total_orders) if total_orders > 0 else 0.0

    cursor.execute('''
        SELECT SUM("AmountPaid") 
        FROM "PAYMENTS" 
        WHERE "PaymentStatus" = 'Paid' 
        AND date("PaymentDate") = date('now', '+8 hours')
    ''')
    sales_today = cursor.fetchone()[0] or 0.0

    cursor.execute('''
        SELECT SUM("AmountPaid") 
        FROM "PAYMENTS" 
        WHERE "PaymentStatus" = 'Paid' 
        AND strftime('%W', "PaymentDate") = strftime('%W', 'now', '+8 hours') 
        AND strftime('%Y', "PaymentDate") = strftime('%Y', 'now', '+8 hours')
    ''')
    sales_week = cursor.fetchone()[0] or 0.0

    cursor.execute('''
        SELECT SUM("AmountPaid") 
        FROM "PAYMENTS" 
        WHERE "PaymentStatus" = 'Paid' 
        AND strftime('%m', "PaymentDate") = strftime('%m', 'now', '+8 hours') 
        AND strftime('%Y', "PaymentDate") = strftime('%Y', 'now', '+8 hours')
    ''')
    sales_month = cursor.fetchone()[0] or 0.0

    cursor.execute('''
        SELECT SUM("AmountPaid") 
        FROM "PAYMENTS" 
        WHERE "PaymentStatus" = 'Paid' 
        AND strftime('%Y', "PaymentDate") = strftime('%Y', 'now', '+8 hours')
    ''')
    sales_year = cursor.fetchone()[0] or 0.0

    cursor.execute(f'''
        SELECT "OrderStatus", COUNT(*) as count 
        FROM "ORDERS" o {where_o} 
        GROUP BY "OrderStatus"
    ''', params_o)
    order_status_counts = {row['OrderStatus']: row['count'] for row in cursor.fetchall()}
    completed_orders = order_status_counts.get('Claimed', 0)
    cancelled_orders = order_status_counts.get('Cancelled', 0)
    pending_orders = sum(v for k, v in order_status_counts.items() if k not in ['Claimed', 'Cancelled'])

    cursor.execute(f'''
        SELECT s."ServiceName", COUNT(od."ServiceID") as TimesAvailed, SUM(od."Subtotal") as Revenue
        FROM "ORDER_DETAILS" od
        JOIN "ORDERS" o ON od."OrderID" = o."OrderID"
        JOIN "SERVICES" s ON od."ServiceID" = s."ServiceID"
        {where_o}
        GROUP BY s."ServiceID"
        ORDER BY TimesAvailed DESC LIMIT 5
    ''', params_o)
    service_report = cursor.fetchall()

    cursor.execute(f'''
        SELECT e."FirstName", COUNT(o."OrderID") as OrdersProcessed
        FROM "ORDERS" o
        JOIN "EMPLOYEES" e ON o."ProcessedByEmpID" = e."EmpID"
        {where_o}
        GROUP BY e."EmpID"
        ORDER BY OrdersProcessed DESC LIMIT 5
    ''', params_o)
    emp_report = cursor.fetchall()

    cursor.execute(f'''
        SELECT "PaymentMethod", COUNT(*) as TxnCount, SUM("AmountPaid") as TotalAmount
        FROM "PAYMENTS" p
        {where_p}
        GROUP BY "PaymentMethod"
    ''', params_p)
    payment_report = cursor.fetchall()

    cursor.execute('''
        SELECT COUNT(*) 
        FROM "CUSTOMERS" 
        WHERE strftime('%m', "DateRegistered") = strftime('%m', 'now', '+8 hours') 
        AND strftime('%Y', "DateRegistered") = strftime('%Y', 'now', '+8 hours')
    ''')
    new_cust_month = cursor.fetchone()[0] or 0

    cursor.execute(f'''
        SELECT c."FirstName", c."LastName", COUNT(o."OrderID") as OrderCount
        FROM "ORDERS" o
        JOIN "CUSTOMERS" c ON o."CustomerID" = c."CustomerID"
        {where_o}
        GROUP BY c."CustomerID"
        ORDER BY OrderCount DESC LIMIT 5
    ''', params_o)
    frequent_customers = cursor.fetchall()

    conn.close()
    
    return render_template('admin-reports.html', 
                           start_date=start_date, end_date=end_date,
                           total_sales=total_sales, total_orders=total_orders,
                           total_customers=total_customers, total_payments=total_payments,
                           avg_order_value=avg_order_value,
                           sales_today=sales_today, sales_week=sales_week,
                           sales_month=sales_month, sales_year=sales_year,
                           completed_orders=completed_orders, pending_orders=pending_orders, cancelled_orders=cancelled_orders,
                           service_report=service_report, emp_report=emp_report,
                           payment_report=payment_report, new_cust_month=new_cust_month, frequent_customers=frequent_customers)

@admin_controller.route('/settings')
def system_settings():
    if not is_admin():
        return redirect(url_for('auth.login'))
        
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    emp_id = session.get('emp_id')
    cursor.execute('''
        SELECT * FROM "EMPLOYEES" 
        WHERE "EmpID" = ?
    ''', (emp_id,))
    admin_data = cursor.fetchone()
    
    cursor.execute('''
        SELECT * FROM "SERVICES" 
        ORDER BY "ServiceID" ASC
    ''')
    services = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin-settings.html', services=services, admin=admin_data)

@admin_controller.route('/settings/update_profile', methods=['POST'])
def update_profile():
    if not is_admin(): return redirect(url_for('auth.login'))
    
    emp_id = session.get('emp_id')
    fname = request.form.get('first_name')
    lname = request.form.get('last_name')
    contact = request.form.get('contact')
    password = request.form.get('password')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    if password and password.strip() != "":
        cursor.execute('''
            UPDATE "EMPLOYEES" 
            SET "FirstName"=?, "LastName"=?, "ContactNumber"=?, "Password"=? 
            WHERE "EmpID"=?
        ''', (fname, lname, contact, password, emp_id))
    else:
        cursor.execute('''
            UPDATE "EMPLOYEES" 
            SET "FirstName"=?, "LastName"=?, "ContactNumber"=? 
            WHERE "EmpID"=?
        ''', (fname, lname, contact, emp_id))
        
    conn.commit()
    session['full_name'] = f"{fname} {lname}" 
    conn.close()
    
    return redirect(url_for('admin.system_settings'))

@admin_controller.route('/settings/add_service', methods=['POST'])
def add_service():
    service_name = request.form.get('service_name')
    description = request.form.get('description', '') 
    unit_type = request.form.get('unit_type')
    rate = request.form.get('rate')

    try:
        conn = sqlite3.connect('laundrify.db', timeout=10)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO "SERVICES" ("ServiceName", "Description", "UnitType", "Rate") 
            VALUES (?, ?, ?, ?)
        ''', (service_name, description, unit_type, rate))
        
        conn.commit()
    except Exception as e:
        print(f"Error adding service: {e}")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin.system_settings'))

@admin_controller.route('/settings/edit_service/<int:id>', methods=['POST'])
def edit_service(id):
    service_name = request.form.get('service_name')
    description = request.form.get('description', '') 
    unit_type = request.form.get('unit_type')
    rate = request.form.get('rate')

    try:
        conn = sqlite3.connect('laundrify.db', timeout=10)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE "SERVICES" 
            SET "ServiceName" = ?, "Description" = ?, "UnitType" = ?, "Rate" = ? 
            WHERE "ServiceID" = ?
        ''', (service_name, description, unit_type, rate, id))
        
        conn.commit()
    except Exception as e:
        print(f"Error updating service: {e}")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin.system_settings'))

@admin_controller.route('/settings/delete_service/<int:id>', methods=['POST'])
def delete_service(id):
    try:
        conn = sqlite3.connect('laundrify.db', timeout=10)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM "SERVICES" 
            WHERE ServiceID = ?
        ''', (id,))
        
        conn.commit()
        
    except Exception as e:
        print(f"ERROR DELETING THE SERVICE: {e}")
        
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin.system_settings'))