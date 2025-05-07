# api/user_routes.py

from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
from functools import wraps
from utils.database import run_query

user_bp = Blueprint('user_bp', __name__)

# Helper to check and decode JWT token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            request.user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated

# GET /api/users
@user_bp.route('', methods=['GET'])
@token_required
def get_all_users():
    try:
        # Only admins can list users
        if request.user['role'] != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        query = "SELECT id, name, email, role FROM users"
        users = run_query(query)
        users_list = [{'id': u[0], 'name': u[1], 'email': u[2], 'role': u[3]} for u in users]
        return jsonify(users_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# POST /api/users
@user_bp.route('/', methods=['POST'])
@token_required
def create_user():
    try:
        if request.user['role'] != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')

        if not all([name, email, password, role]):
            return jsonify({'error': 'Missing fields'}), 400

        query = """
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """
        run_query(query, [name, email, password, role])
        return jsonify({'message': 'User created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# PUT /api/users/<int:user_id>
@user_bp.route('/<int:user_id>', methods=['PUT'])
@token_required
def update_user(user_id):
    try:
        if request.user['role'] != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        role = data.get('role')
        password = data.get('password')
        if password:
            query = """
                UPDATE users
                SET name = ?, email = ?, role = ?, password = ?
                WHERE id = ?
            """
            run_query(query, [name, email, role, password, user_id])
        else:
            query = """
                UPDATE users
                SET name = ?, email = ?, role = ?
                WHERE id = ?
            """
            run_query(query, [name, email, role, user_id])
            
        return jsonify({'message': 'User updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# DELETE /api/users/<int:user_id>
@user_bp.route('/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(user_id):
    try:
        if request.user['role'] != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        query = "DELETE FROM users WHERE id = ?"
        run_query(query, [user_id])
        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
