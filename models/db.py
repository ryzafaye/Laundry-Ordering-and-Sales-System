import sqlite3

DATABASE_NAME = "laundrify.db"

def connect_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "EMPLOYEES" (
        "EmpID" INTEGER,
        "FirstName" TEXT NOT NULL,
        "LastName"  TEXT NOT NULL,
        "Password"  TEXT NOT NULL,
        "Position"  TEXT NOT NULL,
        "ContactNumber" TEXT NOT NULL,
        "Status"    TEXT DEFAULT 'Active',
        "DateCreated"   TEXT DEFAULT CURRENT_DATE,
        PRIMARY KEY("EmpID" AUTOINCREMENT)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "CUSTOMERS" (
        "CustomerID"    INTEGER,
        "FirstName" TEXT NOT NULL,
        "LastName"  TEXT NOT NULL,
        "ContactNumber" TEXT NOT NULL,
        "Address"   TEXT NOT NULL,
        "DateRegistered"    TEXT DEFAULT CURRENT_DATE,
        PRIMARY KEY("CustomerID" AUTOINCREMENT)
        )
    """)

    cursor.execute('SELECT * FROM "EMPLOYEES" WHERE "Position" = ?', ("Admin",))
    user = cursor.fetchone()

    if user is None:
        cursor.execute("""
            INSERT INTO "EMPLOYEES" ("FirstName", "LastName", "Password", "Position", "ContactNumber")
            VALUES (?, ?, ?, ?, ?)
        """, ("System", "Admin", "admin123", "Admin", "09123456789"))
        
        cursor.execute("""
            INSERT INTO "EMPLOYEES" ("FirstName", "LastName", "Password", "Position", "ContactNumber")
            VALUES (?, ?, ?, ?, ?)
        """, ("System", "Staff", "staff123", "Staff", "09987654321"))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "SERVICES" (
        "ServiceID" INTEGER,
        "ServiceName" TEXT NOT NULL,
        "Description" TEXT,
        "Rate" REAL NOT NULL,
        "UnitType" TEXT NOT NULL,
            PRIMARY KEY("ServiceID" AUTOINCREMENT)
            )
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "ORDERS" (
            "OrderID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "CustomerID" INTEGER NOT NULL,
            "ProcessedByEmpID" INTEGER,
            "OrderDate" DATETIME DEFAULT CURRENT_TIMESTAMP,
            "ClaimingMethod" TEXT NOT NULL,
            "OrderStatus" TEXT,
            "TotalAmount" REAL NOT NULL,
            "ClaimedDate" TEXT,
            FOREIGN KEY("CustomerID") REFERENCES "CUSTOMERS"("CustomerID") ON DELETE CASCADE,
            FOREIGN KEY("ProcessedByEmpID") REFERENCES "EMPLOYEES"("EmpID") ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "ORDER_DETAILS" (
            "OrderDetailID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "OrderID" INTEGER NOT NULL,
            "ServiceID" INTEGER NOT NULL,
            "WeightQuantity" REAL NOT NULL,
            "ServicePrice" REAL NOT NULL,
            "Subtotal" REAL NOT NULL,
            FOREIGN KEY("OrderID") REFERENCES "ORDERS"("OrderID") ON DELETE CASCADE,
            FOREIGN KEY("ServiceID") REFERENCES "SERVICES"("ServiceID")
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "PAYMENTS" (
            "PaymentID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "OrderID" INTEGER NOT NULL,
            "PaymentMethod" TEXT NOT NULL,
            "PaymentStatus" TEXT,
            "AmountPaid" REAL NOT NULL,
            "PaymentDate" DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY("OrderID") REFERENCES "ORDERS"("OrderID") ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()