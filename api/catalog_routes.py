# api/catalog_routes.py

from flask import Blueprint, request, jsonify, current_app
import jwt
from core.catalog import get_catalog_items
from utils.database import run_query

catalog_bp = Blueprint("catalog_bp", __name__)
JWT_ALGORITHM = "HS256"

def verify_token(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None, "Missing authorization header"

    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=[JWT_ALGORITHM])
        return payload, None
    except jwt.PyJWTError:
        return None, "Invalid or expired token"

# GET /api/catalog/fetch → fetch from Facebook and save to CSV
@catalog_bp.route('/fetch', methods=['GET'])
def fetch_catalog():
    payload, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    if payload["role"] != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    try:
        get_catalog_items()
        return jsonify({"message": "Catalog fetched and saved successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch catalog: {e}"}), 500
