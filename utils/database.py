# utils/database.py

import os
import pyodbc
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

# Force known good driver
DRIVER = "{ODBC Driver 17 for SQL Server}"  # Hardcoded for now

# Rest from environment
SERVER = os.getenv("AZURE_SQL_SERVER")
DATABASE = os.getenv("AZURE_SQL_DATABASE")
USERNAME = os.getenv("AZURE_SQL_USERNAME")
PASSWORD = os.getenv("AZURE_SQL_PASSWORD")
# Azure SQL Database credentials from environment variables
# SERVER = os.getenv("AZURE_SQL_SERVER")
# DATABASE = os.getenv("AZURE_SQL_DATABASE")
# USERNAME = os.getenv("AZURE_SQL_USERNAME")
# PASSWORD = os.getenv("AZURE_SQL_PASSWORD")
# DRIVER = os.getenv("AZURE_SQL_DRIVER", "{ODBC Driver 17 for SQL Server}")  # Default driver

print("[DEBUG] Connecting with connection string:")
print(f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD=******")

def execute_query(query):
    """
    Connect to Azure SQL and execute a query. Returns rows as list of tuples.
    """
    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD}"
    )

    try:
        with pyodbc.connect(connection_string) as connection:
            cursor = connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    
def upsert_customer(phone_number, username=None):
    """
    Inserts customer if not exists. Returns customer ID.
    """
    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD}"
    )
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            # Try inserting, ignore if already exists
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM customers WHERE phone_number = ?)
                BEGIN
                    INSERT INTO customers (phone_number, username)
                    VALUES (?, ?)
                END
            """, phone_number, phone_number, username)
            conn.commit()

            # Fetch customer ID
            cursor.execute("SELECT id FROM customers WHERE phone_number = ?", phone_number)
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"[DB ERROR] Upsert customer failed: {e}")
        return None


def log_message(customer_id, message_text, direction='incoming', conversation_id=None):

    """
    Logs a message sent or received with the customer.
    """
    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD}"
    )
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (customer_id, message_text, direction, conversation_id)
                VALUES (?, ?, ?, ?)
            """, customer_id, message_text, direction, conversation_id)

            conn.commit()
    except Exception as e:
        print(f"[DB ERROR] Log message failed: {e}")
        return None
    
def get_or_create_conversation(customer_id):
    """
    Checks if there's an active conversation (within 23h) for the customer.
    If not, creates a new conversation and returns its ID.
    """
    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD}"
    )

    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()

            # ✅ Step 1: Try to find recent active conversation
            cursor.execute("""
                SELECT id, started_at FROM conversations
                WHERE customer_id = ? AND status = 'active'
                ORDER BY started_at DESC
            """, customer_id)

            row = cursor.fetchone()

            if row:
                convo_id, started_at = row
                if started_at and datetime.now() - started_at < timedelta(hours=23):
                    print(f"[DEBUG] Reusing active conversation ID: {convo_id}")
                    return convo_id
                else:
                    print(f"[DEBUG] Closing expired conversation ID: {convo_id}")
                    cursor.execute("""
                        UPDATE conversations
                        SET status = 'closed', ended_at = GETDATE()
                        WHERE id = ?
                    """, convo_id)
                    conn.commit()

            # ✅ Step 2: Create a new conversation
            print(f"[DEBUG] Creating new conversation for customer ID: {customer_id}")
            cursor.execute("""
                INSERT INTO conversations (customer_id)
                VALUES (?)
            """, customer_id)

            # 🔥 FETCH ID BEFORE COMMIT (SCOPE_IDENTITY is valid here)
            cursor.execute("SELECT CAST(SCOPE_IDENTITY() AS int)")
            row = cursor.fetchone()
            conn.commit()

            if row and row[0]:
                convo_id = row[0]
                print(f"[DEBUG] New conversation ID: {convo_id}")
                return convo_id
            else:
                print("[DB ERROR] Failed to fetch new conversation ID after insert")
                return None

    except Exception as e:
        print(f"[DB ERROR] get_or_create_conversation failed: {e}")
        return None


def get_conversation_history(conversation_id):
    """
    Returns conversation history in OpenAI-compatible format.
    Example: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    """
    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD}"
    )

    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT direction, message_text FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
            """, conversation_id)

            rows = cursor.fetchall()
            history = []

            for direction, text in rows:
                if direction and text:
                    role = "user" if direction == "incoming" else "assistant"
                    history.append({"role": role, "content": text})

            return history

    except Exception as e:
        print(f"[DB ERROR] get_conversation_history failed: {e}")
        return []


def get_phone_by_customer_id(customer_id):
    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD}"
    )
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT phone_number FROM customers WHERE id = ?", customer_id)
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"[DB ERROR] get_phone_by_customer_id failed: {e}")
        return None

def insert_order(customer_id, order_type, items, total_price, address=None, phone=None, branch=None, customer_name=None):
    """
    Insert a confirmed order into the orders table.
    """
    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD}"
    )
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders (customer_id, order_type, items, total_price, delivery_address, contact_phone, branch, customer_name, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, customer_id, order_type, items, total_price, address, phone, branch, customer_name, "confirmed")
            conn.commit()
            print(f"[DB] Order inserted for customer {customer_id}")
    except Exception as e:
        print(f"[DB ERROR] insert_order failed: {e}")


def get_customer_id_by_phone(phone_number):
    """
    Fetches the customer ID by phone number.
    """
    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD}"
    )
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM customers WHERE phone_number = ?", phone_number)
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"[DB ERROR] get_customer_id_by_phone failed: {e}")
        return None

def run_query(query, params=None, fetchone=False):
    """
    Runs a parameterized query. For SELECT: returns rows.
    For INSERT/UPDATE/DELETE: commits and returns None.
    """
    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD}"
    )
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            
            # If it's a SELECT query
            if query.strip().lower().startswith("select"):
                return cursor.fetchone() if fetchone else cursor.fetchall()
            
            # Otherwise: INSERT/UPDATE/DELETE
            conn.commit()
            return None

    except Exception as e:
        print(f"[DB ERROR] run_query failed: {e}")
        return None
