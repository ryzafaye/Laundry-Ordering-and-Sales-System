from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from models.db import connect_db
import sqlite3
import json

admin_controller = Blueprint('admin', __name__, url_prefix='/admin')

def is_admin():
    return 'user_id' in session and session.get('role') == 'Admin'

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
        WHERE strftime('%m', "PaymentDate") = strftime('%m', 'now', '+8 hours') 
        AND strftime('%Y', "PaymentDate") = strftime('%Y', 'now', '+8 hours')
    ''')
    res = cursor.fetchone()
    monthly_revenue = res[0] if (res and res[0] is not None) else 0.0

    cursor.execute('''
        SELECT COUNT(*) 
        FROM "USERS" u
        JOIN "ROLES" r ON u."RoleID" = r."RoleID"
        WHERE r."RoleName" != 'Admin' AND u."IsActive" = 1
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

    cursor.execute('''SELECT COUNT(*) FROM "CUSTOMERS"''')
    res = cursor.fetchone()
    customer_count = res[0] if (res and res[0] is not None) else 0

    cursor.execute('''
        SELECT SUM("AmountPaid") 
        FROM "PAYMENTS" 
        WHERE date("PaymentDate") = date('now', '+8 hours')
    ''')
    res = cursor.fetchone()
    income_today = res[0] if (res and res[0] is not None) else 0.0

    cursor.execute('''
        SELECT COUNT(*) 
        FROM "ORDERS" 
        WHERE "StatusID" = 'S-04'
    ''')
    res = cursor.fetchone()
    completed_orders = res[0] if (res and res[0] is not None) else 0

    cursor.execute('''
        SELECT 
            o."OrderID", 
            c."FirstName" || ' ' || c."LastName" AS CustomerName,
            u."FirstName" AS StaffName, 
            o."TotalAmount", 
            p."PaymentMethod", 
            os."StatusName"
        FROM "ORDERS" o
        JOIN "CUSTOMERS" c ON o."CustomerID" = c."CustomerID"
        LEFT JOIN "USERS" u ON o."ProcessedByUserID" = u."UserID"
        LEFT JOIN "ORDER_STATUS" os ON o."StatusID" = os."StatusID"
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
        SELECT u.*, r."RoleName" 
        FROM "USERS" u
        JOIN "ROLES" r ON u."RoleID" = r."RoleID"
        WHERE u."IsActive" = 1
    ''')   
    employees = cursor.fetchall()
    
    cursor.execute('SELECT * FROM "ROLES" ORDER BY "RoleID"')
    roles = cursor.fetchall()
    
    total_emp = len(employees)
    admin_count = sum(1 for emp in employees if emp['RoleName'] == 'Admin')
    staff_count = total_emp - admin_count
    
    conn.close()
    
    return render_template('admin-staff.html', 
                           employees=employees, 
                           roles=roles,
                           total_emp=total_emp, 
                           admin_count=admin_count,
                           staff_count=staff_count)

@admin_controller.route('/staff/add', methods=['POST'])
def add_staff():
    if not is_admin(): return redirect(url_for('auth.login'))
    
    fname = request.form.get('fname').strip()
    lname = request.form.get('lname').strip()
    role_id = request.form.get('role_id')
    password = request.form.get('password')
    contact = request.form.get('contact').strip()
    
    if len(contact) != 11 or not contact.startswith('09') or not contact.isdigit():
        flash("Invalid contact number! It must be 11 digits and start with '09'.", "error")
        return redirect(url_for('admin.staff_management'))
    
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT "UserID" FROM "USERS" ORDER BY "UserID" DESC LIMIT 1')
        last_record = cursor.fetchone()
        
        if last_record:
            last_number = int(last_record[0].split('-')[1])
            new_user_id = f"EMP-{last_number + 1:03d}"
        else:
            new_user_id = "EMP-001"

        cursor.execute('''
            INSERT INTO "USERS" ("UserID", "RoleID", "FirstName", "LastName", "Password", "ContactNumber", "IsActive")
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (new_user_id, role_id, fname, lname, password, contact))
        conn.commit()
        flash("New staff added successfully!", "success")
    except Exception as e:
        flash(f"Error saving to database: {e}", "error")
    finally:
        conn.close()
        
    return redirect(url_for('admin.staff_management'))

@admin_controller.route('/staff/edit/<string:user_id>', methods=['POST'])
def edit_staff(user_id):
    if not is_admin(): return redirect(url_for('auth.login'))
    
    fname = request.form.get('fname').strip()
    lname = request.form.get('lname').strip()
    role_id = request.form.get('role_id')
    contact = request.form.get('contact').strip()
    new_password = request.form.get('new_password') 
    
    if len(contact) != 11 or not contact.startswith('09') or not contact.isdigit():
        flash("Invalid contact number! It must be 11 digits and start with '09'.", "error")
        return redirect(url_for('admin.staff_management'))
    
    conn = connect_db()
    cursor = conn.cursor()
    try:
        if new_password and new_password.strip() != "":
            cursor.execute('''
                UPDATE "USERS" 
                SET "FirstName" = ?, "LastName" = ?, "RoleID" = ?, "ContactNumber" = ?, "Password" = ?
                WHERE "UserID" = ?
            ''', (fname, lname, role_id, contact, new_password, user_id))
            flash("Staff record and password updated!", "success")
        else:
            cursor.execute('''
                UPDATE "USERS" 
                SET "FirstName" = ?, "LastName" = ?, "RoleID" = ?, "ContactNumber" = ?
                WHERE "UserID" = ?
            ''', (fname, lname, role_id, contact, user_id))
            flash("Staff record updated!", "success")
            
        conn.commit()
    except Exception as e:
        flash(f"Error updating database: {e}", "error")
    finally:
        conn.close()
    
    return redirect(url_for('admin.staff_management'))

@admin_controller.route('/staff/delete/<string:user_id>', methods=['POST'])
def delete_staff(user_id):
    if not is_admin(): return redirect(url_for('auth.login'))
    
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE "USERS" 
            SET "IsActive" = 0 
            WHERE "UserID" = ?
        ''', (user_id,))
        conn.commit()
        flash("Staff account deactivated successfully.", "success")
    except Exception as e:
        flash(f"Cannot delete: {e}", "error")
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
            o."OrderID", o."OrderDate", o."ClaimedDate", o."TotalAmount", o."ClaimingMethod", 
            os."StatusName",
            c."FirstName" AS CustFirstName, c."LastName" AS CustLastName, c."CustomerID",
            p."PaymentMethod",
            u."FirstName" AS EmpFirstName, u."LastName" AS EmpLastName
        FROM "ORDERS" o
        LEFT JOIN "CUSTOMERS" c ON o."CustomerID" = c."CustomerID"
        LEFT JOIN "PAYMENTS" p ON o."OrderID" = p."OrderID"
        LEFT JOIN "USERS" u ON o."ProcessedByUserID" = u."UserID"
        LEFT JOIN "ORDER_STATUS" os ON o."StatusID" = os."StatusID"
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
        
        services_list = [{'name': s['ServiceName'], 'qty': s['WeightQuantity'], 'subtotal': s['Subtotal']} for s in services_data]
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
    
    where_o = "WHERE o.\"StatusID\" != 'S-05'"
    params_o = []

    if start_date and end_date:
        where_o += " AND date(o.\"OrderDate\") BETWEEN ? AND ?"
        params_o.extend([start_date, end_date])

    cursor.execute(f'''
        SELECT SUM(o."TotalAmount") as TotalSales, COUNT(o."OrderID") as TotalOrders 
        FROM "ORDERS" o {where_o}
    ''', params_o)
    core_res = cursor.fetchone()
    total_sales = core_res['TotalSales'] or 0.0
    total_orders = core_res['TotalOrders'] or 0
    avg_order_value = (total_sales / total_orders) if total_orders > 0 else 0.0

    cursor.execute('SELECT COUNT(*) FROM "CUSTOMERS"')
    total_customers = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM("AmountPaid") FROM "PAYMENTS" WHERE date("PaymentDate") = date("now", "+8 hours")')
    sales_today = cursor.fetchone()[0] or 0.0

    cursor.execute('SELECT SUM("AmountPaid") FROM "PAYMENTS" WHERE strftime("%W", "PaymentDate") = strftime("%W", "now", "+8 hours") AND strftime("%Y", "PaymentDate") = strftime("%Y", "now", "+8 hours")')
    sales_week = cursor.fetchone()[0] or 0.0

    cursor.execute('SELECT SUM("AmountPaid") FROM "PAYMENTS" WHERE strftime("%m", "PaymentDate") = strftime("%m", "now", "+8 hours") AND strftime("%Y", "PaymentDate") = strftime("%Y", "now", "+8 hours")')
    sales_month = cursor.fetchone()[0] or 0.0

    where_all_status = "WHERE 1=1"
    if start_date and end_date:
        where_all_status += " AND date(o.\"OrderDate\") BETWEEN ? AND ?"

    cursor.execute(f'''
        SELECT os."StatusName", COUNT(o."OrderID") as count 
        FROM "ORDERS" o 
        JOIN "ORDER_STATUS" os ON o."StatusID" = os."StatusID"
        {where_all_status}
        GROUP BY os."StatusID"
    ''', params_o)
    status_distribution = cursor.fetchall()

    cursor.execute(f'''
        SELECT s."ServiceName", COUNT(od."ServiceID") as TimesAvailed, SUM(od."Subtotal") as Revenue
        FROM "ORDER_DETAILS" od
        JOIN "ORDERS" o ON od."OrderID" = o."OrderID"
        JOIN "SERVICES" s ON od."ServiceID" = s."ServiceID"
        {where_o}
        GROUP BY s."ServiceID"
        ORDER BY Revenue DESC LIMIT 5
    ''', params_o)
    service_report = cursor.fetchall()

    cursor.execute(f'''
        SELECT u."FirstName", COUNT(o."OrderID") as OrdersProcessed, SUM(o."TotalAmount") as RevenueGenerated
        FROM "ORDERS" o
        JOIN "USERS" u ON o."ProcessedByUserID" = u."UserID"
        {where_o}
        GROUP BY u."UserID"
        ORDER BY RevenueGenerated DESC LIMIT 5
    ''', params_o)
    emp_report = cursor.fetchall()

    cursor.execute(f'''
        SELECT p."PaymentMethod", COUNT(p."OrderID") as TxnCount, SUM(p."AmountPaid") as TotalAmount
        FROM "PAYMENTS" p
        JOIN "ORDERS" o ON p."OrderID" = o."OrderID"
        {where_o}
        GROUP BY p."PaymentMethod"
    ''', params_o)
    payment_report = cursor.fetchall()

    cursor.execute(f'''
        SELECT o."ClaimingMethod", COUNT(o."OrderID") as TxnCount, SUM(o."TotalAmount") as TotalAmount
        FROM "ORDERS" o
        {where_o}
        GROUP BY o."ClaimingMethod"
    ''', params_o)
    claiming_report = cursor.fetchall()

    cursor.execute(f'''
        SELECT c."FirstName", c."LastName", COUNT(o."OrderID") as OrderCount, SUM(o."TotalAmount") as TotalSpent
        FROM "ORDERS" o
        JOIN "CUSTOMERS" c ON o."CustomerID" = c."CustomerID"
        {where_o}
        GROUP BY c."CustomerID"
        ORDER BY TotalSpent DESC LIMIT 5
    ''', params_o)
    frequent_customers = cursor.fetchall()

    conn.close()
    
    return render_template('admin-reports.html', 
                           start_date=start_date, end_date=end_date,
                           total_sales=total_sales, total_orders=total_orders,
                           total_customers=total_customers, avg_order_value=avg_order_value,
                           sales_today=sales_today, sales_week=sales_week, sales_month=sales_month,
                           status_distribution=status_distribution,
                           service_report=service_report, emp_report=emp_report,
                           payment_report=payment_report, claiming_report=claiming_report, 
                           frequent_customers=frequent_customers)

@admin_controller.route('/settings')
def system_settings():
    if not is_admin():
        return redirect(url_for('auth.login'))
        
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    user_id = session.get('user_id')
    cursor.execute('''
        SELECT * FROM "USERS" 
        WHERE "UserID" = ?
    ''', (user_id,))
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
    
    user_id = session.get('user_id')
    fname = request.form.get('first_name')
    lname = request.form.get('last_name')
    contact = request.form.get('contact')
    password = request.form.get('password')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    if password and password.strip() != "":
        cursor.execute('''
            UPDATE "USERS" 
            SET "FirstName"=?, "LastName"=?, "ContactNumber"=?, "Password"=? 
            WHERE "UserID"=?
        ''', (fname, lname, contact, password, user_id))
    else:
        cursor.execute('''
            UPDATE "USERS" 
            SET "FirstName"=?, "LastName"=?, "ContactNumber"=? 
            WHERE "UserID"=?
        ''', (fname, lname, contact, user_id))
        
    conn.commit()
    session['full_name'] = f"{fname} {lname}" 
    conn.close()
    
    flash("Profile updated successfully!", "success")
    return redirect(url_for('admin.system_settings'))

@admin_controller.route('/settings/add_service', methods=['POST'])
def add_service():
    if not is_admin(): return redirect(url_for('auth.login'))
    
    service_name = request.form.get('service_name').strip()
    description = request.form.get('description', '').strip() 
    unit_type = request.form.get('unit_type')
    rate = request.form.get('rate')

    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT "ServiceID" FROM "SERVICES" ORDER BY "ServiceID" DESC LIMIT 1')
        last_record = cursor.fetchone()
        
        if last_record:
            last_number = int(last_record[0].split('-')[1])
            new_srv_id = f"SRV-{last_number + 1:02d}"
        else:
            new_srv_id = "SRV-01"
        
        cursor.execute('''
            INSERT INTO "SERVICES" ("ServiceID", "ServiceName", "Description", "UnitType", "Rate") 
            VALUES (?, ?, ?, ?, ?)
        ''', (new_srv_id, service_name, description, unit_type, rate))
        
        conn.commit()
        flash("New service added successfully!", "success")
    except Exception as e:
        flash(f"Error adding service: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin.system_settings'))

@admin_controller.route('/settings/edit_service/<string:srv_id>', methods=['POST'])
def edit_service(srv_id):
    if not is_admin(): return redirect(url_for('auth.login'))
    
    service_name = request.form.get('service_name').strip()
    description = request.form.get('description', '').strip() 
    unit_type = request.form.get('unit_type')
    rate = request.form.get('rate')

    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE "SERVICES" 
            SET "ServiceName" = ?, "Description" = ?, "UnitType" = ?, "Rate" = ? 
            WHERE "ServiceID" = ?
        ''', (service_name, description, unit_type, rate, srv_id))
        
        conn.commit()
        flash("Service updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating service: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin.system_settings'))

@admin_controller.route('/settings/delete_service/<string:srv_id>', methods=['POST'])
def delete_service(srv_id):
    if not is_admin(): return redirect(url_for('auth.login'))
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM "SERVICES" 
            WHERE "ServiceID" = ?
        ''', (srv_id,))
        
        conn.commit()
        flash("Service deleted successfully!", "success")
        
    except Exception as e:
        flash("Cannot delete service: It is currently linked to existing order transactions.", "error")
        
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin.system_settings'))