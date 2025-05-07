# api/customers_routes.py

from flask import Blueprint, request, jsonify, current_app
import jwt
from utils.database import run_query

customer_bp = Blueprint('customer_bp', __name__)

JWT_ALGORITHM = "HS256"

def verify_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None, "Missing authorization header"

    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=[JWT_ALGORITHM])
        return payload, None
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None, "Invalid or expired token"

# GET /api/customers (with pagination and search)
@customer_bp.route('/', methods=['GET'])
def get_customers():
    payload, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    if payload['role'] not in ['admin', 'agent']:
        return jsonify({"error": "Unauthorized"}), 403

    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    search = request.args.get('search', '').strip()

    offset = (page - 1) * limit

    query = """
        SELECT id, phone_number, username, created_at
        FROM dbo.customers
    """
    params = []

    if search:
        query += " WHERE phone_number LIKE ? OR username LIKE ?"
        params += [f"%{search}%", f"%{search}%"]

    query += " ORDER BY created_at DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    params += [offset, limit]

    customers = run_query(query, params)

    customer_list = []
    for cust in customers:
        customer_list.append({
            "id": cust[0],
            "phone_number": cust[1],
            "username": cust[2],
            "created_at": cust[3]
        })

    return jsonify(customer_list), 200
