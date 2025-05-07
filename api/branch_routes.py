# api/branch_routes.py

from flask import Blueprint, request, jsonify, current_app
import jwt
from utils.database import run_query

branch_bp = Blueprint('branch_bp', __name__)

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

# GET /api/branches
@branch_bp.route('', methods=['GET'])
def get_branches():
    payload, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    if payload['role'] not in ['admin', 'agent']:
        return jsonify({"error": "Unauthorized"}), 403

    branches = run_query("""
        SELECT id, name, location, delivery_time
        FROM dbo.branches
        ORDER BY id DESC
    """)

    branch_list = []
    for branch in branches:
        branch_list.append({
            "id": branch[0],
            "name": branch[1],
            "location": branch[2],
            "delivery_time": branch[3]
        })

    return jsonify(branch_list), 200

# POST /api/branches
@branch_bp.route('/', methods=['POST'])
def create_branch():
    payload, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    if payload['role'] not in ['admin', 'agent']:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    name = data.get('name')
    location = data.get('location')
    delivery_time = data.get('delivery_time')

    if not name or not location or not delivery_time:
        return jsonify({"error": "Missing required fields"}), 400

    run_query("""
        INSERT INTO dbo.branches (name, location, delivery_time)
        VALUES (?, ?, ?)
    """, params=(name, location, delivery_time))

    return jsonify({"message": "Branch created successfully."}), 201

# PUT /api/branches/<branch_id>
@branch_bp.route('/<int:branch_id>', methods=['PUT'])
def update_branch(branch_id):
    payload, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    if payload['role'] not in ['admin', 'agent']:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    name = data.get('name')
    location = data.get('location')
    delivery_time = data.get('delivery_time')

    if not (name or location or delivery_time):
        return jsonify({"error": "No update fields provided"}), 400

    updates = []
    params = []

    if name:
        updates.append("name = ?")
        params.append(name)
    if location:
        updates.append("location = ?")
        params.append(location)
    if delivery_time:
        updates.append("delivery_time = ?")
        params.append(delivery_time)

    params.append(branch_id)

    query = f"UPDATE dbo.branches SET {', '.join(updates)} WHERE id = ?"

    run_query(query, params=params)

    return jsonify({"message": "Branch updated successfully."}), 200

# DELETE /api/branches/<branch_id>
@branch_bp.route('/<int:branch_id>', methods=['DELETE'])
def delete_branch(branch_id):
    payload, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    if payload['role'] != 'admin':
        return jsonify({"error": "Only admins can delete branches"}), 403

    run_query("DELETE FROM dbo.branches WHERE id = ?", params=(branch_id,))

    return jsonify({"message": "Branch deleted successfully."}), 200
