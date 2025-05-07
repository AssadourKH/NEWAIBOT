# api/conversation_routes.py

from flask import Blueprint, request, jsonify, current_app
import jwt
from utils.database import run_query
from datetime import datetime

conversation_bp = Blueprint('conversation_bp', __name__)

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

# GET /api/conversations (pagination + agent filter)
@conversation_bp.route('', methods=['GET'])
def get_conversations():
    payload, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    if payload['role'] not in ['admin', 'agent']:
        return jsonify({"error": "Unauthorized"}), 403

    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    offset = (page - 1) * limit

    today_str = datetime.now().strftime('%Y-%m-%d')

    query = """
        SELECT c.id, c.customer_id, c.started_at, c.ended_at, c.status, cu.username
        FROM dbo.conversations c
        LEFT JOIN dbo.customers cu ON c.customer_id = cu.id
    """
    filters = []
    params = []

    if payload['role'] == 'agent':
        filters.append("CAST(c.started_at AS DATE) = ?")
        params.append(today_str)

    elif payload['role'] == 'admin':
        date_filter = request.args.get('date')
        if date_filter:
            filters.append("CAST(c.started_at AS DATE) = ?")
            params.append(date_filter)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY c.started_at DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    params += [offset, limit]

    conversations = run_query(query, params)

    if conversations is None:
        return jsonify({"error": "Database query failed"}), 500

    conversation_list = []
    for conv in conversations:
        conversation_list.append({
            "id": conv[0],
            "customer_id": conv[1],
            "started_at": conv[2],
            "ended_at": conv[3],
            "status": conv[4],
            "customer_name": conv[5] or f"Customer #{conv[1]}"
        })

    return jsonify(conversation_list), 200


# GET /api/conversations/<id>/messages
@conversation_bp.route('/<int:conversation_id>/messages', methods=['GET'])
def get_conversation_messages(conversation_id):
    payload, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    if payload['role'] not in ['admin', 'agent']:
        return jsonify({"error": "Unauthorized"}), 403

    query = """
        SELECT id, customer_id, conversation_id, message_text, direction, timestamp
        FROM dbo.messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
    """
    rows = run_query(query, [conversation_id])

    if rows is None:
        return jsonify({"error": "Failed to retrieve messages"}), 500

    messages = []
    for row in rows:
        messages.append({
            "id": row[0],
            "customer_id": row[1],
            "conversation_id": row[2],
            "message_text": row[3],
            "direction": row[4],
            "timestamp": row[5]
        })

    return jsonify(messages), 200
