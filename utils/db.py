import os
import mysql.connector
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """Create and return a new database connection."""

    try:
        db_url = os.environ.get("MYSQL_URL")

        if db_url:
            # Production
            url = urlparse(db_url)

            db = mysql.connector.connect(
                host=url.hostname,
                port=url.port or 3306,
                user=url.username,
                password=url.password,
                database=url.path[1:] if url.path else None
            )

        else:
            # Local development
            db = mysql.connector.connect(
                host=os.environ.get("DB_HOST", "localhost"),
                user=os.environ.get("DB_USER", "root"),
                password=os.environ.get("DB_PASS", ""),
                database=os.environ.get("DB_NAME", "expense_tracker"),
                port=int(os.environ.get("DB_PORT", 3306))
            )

        return db

    except mysql.connector.Error as exc:
        print(f"DB CONNECTION ERROR: {exc}")
        return None


def get_cursor(dictionary=False):
    """Get a cursor plus its owning database connection."""

    db = get_db_connection()

    if db is None:
        return None, None

    cursor = db.cursor(dictionary=dictionary)

    return cursor, db


def close_connection(cursor=None, db=None):
    """Safely close a cursor and database connection."""

    try:
        if cursor:
            cursor.close()
    finally:
        if db and db.is_connected():
            db.close()


def create_tables():
    """Create all required tables if they don't exist."""
    db = get_db_connection()
    if db is None:
        print("Could not connect to database to create tables.")
        return

    try:
        cursor = db.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(100) NOT NULL,
                type ENUM('bank','wallet','cash','credit_card') NOT NULL DEFAULT 'bank',
                initial_balance DECIMAL(15,2) DEFAULT 0.00,
                current_balance DECIMAL(15,2) DEFAULT 0.00,
                icon VARCHAR(50),
                color VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(100) NOT NULL,
                icon VARCHAR(50),
                color VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Subcategories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subcategories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                category_id INT NOT NULL,
                name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        """)

        # Expenses / Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                account_id INT NOT NULL,
                category_id INT,
                subcategory_id INT,
                type ENUM('income','expense') NOT NULL DEFAULT 'expense',
                amount DECIMAL(15,2) NOT NULL,
                pay_method ENUM('cash','upi','debit_card','credit_card','net_banking') NOT NULL DEFAULT 'cash',
                note TEXT,
                exp_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
                FOREIGN KEY (subcategory_id) REFERENCES subcategories(id) ON DELETE SET NULL
            )
        """)

        # Transfers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                from_account_id INT NOT NULL,
                to_account_id INT NOT NULL,
                amount DECIMAL(15,2) NOT NULL,
                note TEXT,
                transfer_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (from_account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (to_account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
        """)

        # Budget table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget (
                id INT AUTO_INCREMENT PRIMARY KEY,
                month VARCHAR(7) NOT NULL,
                budget_amount DECIMAL(15,2) NOT NULL,
                user_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        db.commit()
        print("Database tables verified.")

    except Exception as e:
        print(f"Error creating tables: {e}")
        db.rollback()

    finally:
        db.close()
