from flask import Flask, redirect, url_for, session
from models.db import create_tables
from controllers.auth_controller import auth_controller
from controllers.customer_controller import customer_controller
from controllers.service_controller import service_controller
from controllers.order_controller import order_controller
from controllers.queue_controller import queue_controller
from controllers.history_controller import history_controller
from controllers.dashboard_controller import dashboard_controller
from controllers.admin_controller import admin_controller

app = Flask(__name__)
app.secret_key = "laundrify-secret-key-2026"

create_tables()

app.register_blueprint(auth_controller) 
app.register_blueprint(customer_controller)
app.register_blueprint(service_controller)
app.register_blueprint(order_controller)
app.register_blueprint(queue_controller)
app.register_blueprint(history_controller)
app.register_blueprint(dashboard_controller)
app.register_blueprint(admin_controller)

@app.route('/')
def index():
    if 'emp_id' in session:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(debug=True, port=8000)