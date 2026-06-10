import sqlite3

DATABASE_NAME = "laundrify.db"

def connect_db():
    conn = sqlite3.connect(DATABASE_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "ROLES" (
            "RoleID" TEXT,
            "RoleName" TEXT NOT NULL,
            PRIMARY KEY ("RoleID")
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "USERS" (
            "UserID" TEXT,
            "RoleID" TEXT NOT NULL,
            "FirstName" TEXT NOT NULL,
            "LastName" TEXT NOT NULL,
            "Password" TEXT NOT NULL,
            "ContactNumber" TEXT NOT NULL,
            "IsActive" INTEGER DEFAULT 1,
            PRIMARY KEY ("UserID"),
            FOREIGN KEY ("RoleID") REFERENCES "ROLES"("RoleID") ON DELETE RESTRICT ON UPDATE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "ORDER_STATUS" (
            "StatusID" TEXT,
            "StatusName" TEXT NOT NULL,
            PRIMARY KEY ("StatusID")
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "CUSTOMERS" (
            "CustomerID" TEXT,
            "FirstName" TEXT NOT NULL,
            "LastName" TEXT NOT NULL,
            "ContactNumber" TEXT NOT NULL,
            "Address" TEXT NOT NULL,
            PRIMARY KEY ("CustomerID")
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "SERVICES" (
            "ServiceID" TEXT,
            "ServiceName" TEXT NOT NULL,
            "Description" TEXT,
            "Rate" REAL NOT NULL,
            "UnitType" TEXT NOT NULL,
            PRIMARY KEY ("ServiceID")
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "ORDERS" (
            "OrderID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "CustomerID" TEXT NOT NULL,
            "ProcessedByUserID" TEXT NOT NULL,
            "StatusID" TEXT NOT NULL,
            "TotalAmount" REAL NOT NULL,
            "ClaimingMethod" TEXT NOT NULL,
            "OrderDate" TEXT DEFAULT CURRENT_TIMESTAMP,
            "ClaimedDate" TEXT,
            FOREIGN KEY ("CustomerID") REFERENCES "CUSTOMERS"("CustomerID") ON DELETE RESTRICT ON UPDATE CASCADE,
            FOREIGN KEY ("ProcessedByUserID") REFERENCES "USERS"("UserID") ON DELETE RESTRICT ON UPDATE CASCADE,
            FOREIGN KEY ("StatusID") REFERENCES "ORDER_STATUS"("StatusID") ON DELETE RESTRICT ON UPDATE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "ORDER_DETAILS" (
            "OrderID" INTEGER NOT NULL,
            "ServiceID" TEXT NOT NULL,
            "WeightQuantity" REAL NOT NULL,
            "ServicePrice" REAL NOT NULL,
            "Subtotal" REAL NOT NULL,
            PRIMARY KEY ("OrderID", "ServiceID"),
            FOREIGN KEY ("OrderID") REFERENCES "ORDERS"("OrderID") ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY ("ServiceID") REFERENCES "SERVICES"("ServiceID") ON DELETE RESTRICT ON UPDATE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "PAYMENTS" (
            "OrderID" INTEGER NOT NULL,
            "AmountPaid" REAL NOT NULL,
            "PaymentMethod" TEXT NOT NULL,
            "PaymentDate" TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY ("OrderID"),
            FOREIGN KEY ("OrderID") REFERENCES "ORDERS"("OrderID") ON DELETE CASCADE ON UPDATE CASCADE
        )
    """)

    cursor.execute('SELECT COUNT(*) FROM "ROLES"')
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO "ROLES" ("RoleID", "RoleName") VALUES (?, ?)
        ''', [
            ('R-01', 'Admin'),
            ('R-02', 'Staff')
        ])

        cursor.executemany('''
            INSERT INTO "ORDER_STATUS" ("StatusID", "StatusName") VALUES (?, ?)
        ''', [
            ('S-01', 'Pending'),
            ('S-02', 'Processing'),
            ('S-03', 'Ready'),
            ('S-04', 'Claimed'),
            ('S-05', 'Cancelled')
        ])

        cursor.execute("""
            INSERT INTO "USERS" ("UserID", "RoleID", "FirstName", "LastName", "Password", "ContactNumber", "IsActive")
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("EMP-001", "R-01", "System", "Admin", "admin123", "09123456789", 1))
        
        cursor.execute("""
            INSERT INTO "USERS" ("UserID", "RoleID", "FirstName", "LastName", "Password", "ContactNumber", "IsActive")
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("EMP-002", "R-02", "System", "Staff", "staff123", "09987654321", 1))

    conn.commit()
    conn.close()