from flask import Blueprint, request, jsonify, current_app
import jwt
from utils.database import run_query
from datetime import datetime

order_bp = Blueprint('order_bp', __name__)
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

# GET /api/orders (admin = all, agent = today only)
@order_bp.route('', methods=['GET'])
def get_orders():
    payload, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    if payload['role'] not in ['admin', 'agent']:
        return jsonify({"error": "Unauthorized"}), 403

    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    status_filter = request.args.get('status')
    offset = (page - 1) * limit
    today_str = datetime.now().strftime('%Y-%m-%d')

    query = """
        SELECT o.id,
            o.customer_id,
            o.order_type,
            o.items,
            o.total_price,
            o.delivery_address,
            COALESCE(o.contact_phone, c.phone_number) AS contact_phone,
            o.branch,
            COALESCE(o.customer_name, c.username) AS customer_name,
            o.created_at,
            o.status
        FROM dbo.orders o
        LEFT JOIN dbo.customers c ON o.customer_id = c.id
    """

    params = []
    filters = []

    if payload['role'] == 'agent':
        filters.append("CAST(o.created_at AS DATE) = ?")
        params.append(today_str)

    if status_filter:
        filters.append("status = ?")
        params.append(status_filter)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY created_at DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    params += [offset, limit]

    rows = run_query(query, params)
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "customer_id": row[1],
            "order_type": row[2],
            "items": row[3],
            "total_price": row[4],
            "delivery_address": row[5],
            "contact_phone": row[6],
            "branch": row[7],
            "customer_name": row[8],  # now from joined table
            "created_at": row[9],
            "status": row[10]
        })

    return jsonify(result), 200

# PUT /api/orders/<id>/status
@order_bp.route('/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    payload, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    if payload['role'] not in ['admin', 'agent']:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    new_status = data.get("status")

    if new_status not in ["confirmed", "preparing", "completed"]:
        return jsonify({"error": "Invalid status value"}), 400

    run_query("UPDATE dbo.orders SET status = ? WHERE id = ?", [new_status, order_id])
    return jsonify({"message": "Status updated"}), 200
