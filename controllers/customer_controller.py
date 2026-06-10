from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from models.db import connect_db
from datetime import datetime, timezone, timedelta

customer_controller = Blueprint('customer', __name__)

def is_logged_in():
    return 'emp_id' in session

@customer_controller.route('/customers')
def customers():
    if not is_logged_in(): return redirect(url_for('auth.login'))
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM "CUSTOMERS" ORDER BY "CustomerID" DESC')
    all_customers = cursor.fetchall()
    conn.close()
    
    return render_template('customers.html', customers=all_customers)

@customer_controller.route('/add_customer', methods=['POST'])
def add_customer():
    if not is_logged_in(): return redirect(url_for('auth.login'))

    fname = request.form.get('fname').strip()
    lname = request.form.get('lname').strip()
    phone = request.form.get('phone').strip()
    address = request.form.get('address').strip()

    PHT = timezone(timedelta(hours=8))
    current_pht_time = datetime.now(PHT).strftime('%Y-%m-%d')

    if not fname or not lname or not phone or not address:
        flash('Registration failed: All fields are required!', 'error')
        return redirect(url_for('customer.customers')) 

    clean_phone = ''.join(filter(str.isdigit, phone))
    
    if len(clean_phone) != 11 or not clean_phone.startswith('09'):
        flash('Registration failed: Contact number must be exactly 11 digits and start with 09.', 'error')
        return redirect(url_for('customer.customers'))

    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO "CUSTOMERS" ("FirstName", "LastName", "ContactNumber", "Address", "DateRegistered")
            VALUES (?, ?, ?, ?, ?)
        """, (fname, lname, clean_phone, address, current_pht_time))
        conn.commit()
        conn.close()
        flash('New customer successfully registered!', 'success')
    except Exception as e:
        flash(f'Database Error: {str(e)}', 'error')

    return redirect(url_for('customer.customers'))

@customer_controller.route('/edit_customer', methods=['POST'])
def edit_customer():
    if not is_logged_in(): return redirect(url_for('auth.login'))

    cust_id = request.form.get('cust_id')
    fname = request.form.get('edit_fname').strip()
    lname = request.form.get('edit_lname').strip()
    phone = request.form.get('edit_phone').strip()
    address = request.form.get('edit_address').strip()

    clean_phone = ''.join(filter(str.isdigit, phone))
    if len(clean_phone) != 11 or not clean_phone.startswith('09'):
        flash('Update failed: Invalid contact number format.', 'error')
        return redirect(url_for('customer.customers'))

    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE "CUSTOMERS" 
            SET "FirstName" = ?, "LastName" = ?, "ContactNumber" = ?, "Address" = ?
            WHERE "CustomerID" = ?
        """, (fname, lname, clean_phone, address, cust_id))
        conn.commit()
        conn.close()
        flash('Customer record successfully updated!', 'success')
    except Exception as e:
        flash(f'Update Error: {str(e)}', 'error')

    return redirect(url_for('customer.customers'))

@customer_controller.route('/delete_customer', methods=['POST'])
def delete_customer():
    if not is_logged_in(): return redirect(url_for('auth.login'))

    cust_id = request.form.get('delete_cust_id')

    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM "CUSTOMERS" WHERE "CustomerID" = ?', (cust_id,))
        conn.commit()
        conn.close()
        flash('Customer record has been deleted.', 'success')
    except Exception as e:
        flash(f'Delete Error: {str(e)}', 'error')

    return redirect(url_for('customer.customers'))