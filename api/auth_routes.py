# api/auth_routes.py

from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
from utils.database import run_query

auth_bp = Blueprint('auth_bp', __name__)

JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 30 * 24 * 60 * 60  # 30 days

# POST /api/auth/login
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Fetch user
    user = run_query(
        "SELECT id, name, email, role FROM dbo.users WHERE email = ? AND password = ?", 
        (email, password),
        fetchone=True
    )

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    user_id, name, email, role = user

    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    }

    token = jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm=JWT_ALGORITHM)

    return jsonify({
        "token": token,
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
            "role": role
        }
    }), 200

# GET /api/auth/me
@auth_bp.route('/me', methods=['GET'])
def me():
    auth_header = request.headers.get('Authorization')

    if not auth_header:
        return jsonify({"error": "Authorization header missing"}), 401

    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return jsonify({"error": "Invalid or expired token"}), 401

    return jsonify({
        "user_id": payload["user_id"],
        "email": payload["email"],
        "role": payload["role"]
    }), 200
