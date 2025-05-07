from flask import Flask, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import requests
import re
import pandas as pd
from core import process_message
from core import user_order_context, confirm_order
from core.voice import transcribe_audio_bytes
from utils import database
from core.catalog import get_catalog_items
import time
from collections import defaultdict

# Import your API routes
from api.auth_routes import auth_bp
from api.user_routes import user_bp
from api.orders_routes import order_bp
from api.branch_routes import branch_bp
from api.conversation_routes import conversation_bp
from api.customers_routes import customer_bp
from api.catalog_routes import catalog_bp

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {
    "origins": "https://malakbotdashboard-fdbwhve4bvcbfxaz.westus-01.azurewebsites.net"
}}, supports_credentials=True, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

load_dotenv()



# Config
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
# Register Blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(user_bp, url_prefix="/api/users")
app.register_blueprint(order_bp, url_prefix="/api/orders")
app.register_blueprint(branch_bp, url_prefix="/api/branches")
app.register_blueprint(conversation_bp, url_prefix="/api/conversations")
app.register_blueprint(customer_bp, url_prefix="/api/customers")
app.register_blueprint(catalog_bp, url_prefix="/api/catalog")

# Meta WhatsApp API config
META_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")  # Token to verify webhook
META_API_VERSION = "v22.0"
TEMPLATE_NAME = "order_confirmation"


META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

# Cache to store messages per user
recent_messages_cache = defaultdict(lambda: {"last_message_time": 0, "buffer": []})
MERGE_TIMEOUT_SECONDS = 5

# Load catalog once at module level
try:
    catalog_df = pd.read_csv("final_catalog_match.csv")
    
    catalog_lookup = {
        row["retailer_id"]: {
            "name": row["name"],
            "price": int(row["price"]) if pd.notna(row["price"]) else 0,
            "currency": row.get("currency", "LBP")
        }
        for _, row in catalog_df.iterrows()
    }
except Exception as e:
    print(f"[ERROR] Could not load catalog CSV: {e}")
    catalog_lookup = {}



def get_media_url_from_meta(media_id):
    """
    Fetch the real URL of the media file using Meta API.
    """
    url = f"https://graph.facebook.com/v22.0/{media_id}"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    if response.ok:
        media_info = response.json()
        return media_info.get("url")
    else:
        print(f"[META ERROR] Failed to fetch media URL: {response.text}")
        return None

def transcribe_audio_from_url(audio_url):
    try:
        headers = {"Authorization": f"Bearer {META_TOKEN}"}
        audio_response = requests.get(audio_url, headers=headers)
        audio_response.raise_for_status()

        audio_data = audio_response.content
        transcription = transcribe_audio_bytes(audio_data)
        return transcription
    except Exception as e:
        print(f"[TRANSCRIBE ERROR] {e}")
        return None

# Send a plain text message via Meta API
def send_text_via_meta(to_number, text):
    url = f"https://graph.facebook.com/{META_API_VERSION}/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    try:
        r = requests.post(url, headers=headers, json=payload)
        r.raise_for_status()
        print(f"[META] ✅ Text sent to {to_number}")
    except Exception as e:
        print(f"[META ERROR] ❌ {e}")

# Send a template message via Meta API
def send_template_via_meta(to_number, full_summary_text):
    url = f"https://graph.facebook.com/{META_API_VERSION}/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        # Extract fields using regex
        items_match = re.search(r"\* Items:\s*(.+)", full_summary_text)
        total_price_match = re.search(r"\* Total Price:\s*(.+)", full_summary_text)
        address_match = re.search(r"\* Delivery Address:\s*(.+)", full_summary_text)
        pickup_branch_match = re.search(r"\* Pickup Branch:\s*(.+)", full_summary_text)
        phone_match = re.search(r"\* Contact Phone:\s*(.+)", full_summary_text)
        customer_name_match = re.search(r"\* Customer Name:\s*(.+)", full_summary_text)

        # Prepare default empty strings
        items = items_match.group(1).strip() if items_match else ""
        total_price = total_price_match.group(1).strip() if total_price_match else ""
        delivery_address = address_match.group(1).strip() if address_match else ""
        pickup_branch = pickup_branch_match.group(1).strip() if pickup_branch_match else ""
        phone = phone_match.group(1).strip() if phone_match else ""
        customer_name = customer_name_match.group(1).strip() if customer_name_match else ""

        # Now prepare parameters according to order type
        if delivery_address:
            # 🚚 Delivery
            parameters = [
                {"type": "text", "text": items},
                {"type": "text", "text": total_price},
                {"type": "text", "text": delivery_address},
                {"type": "text", "text": phone}
            ]
        elif pickup_branch:
            # 🛍️ Takeaway
            parameters = [
                {"type": "text", "text": items},
                {"type": "text", "text": total_price},
                {"type": "text", "text": pickup_branch},
                {"type": "text", "text": customer_name}
            ]
        else:
            parameters = [
                {"type": "text", "text": full_summary_text.replace("\n", " ").strip() or "-"},
                {"type": "text", "text": "-"},
                {"type": "text", "text": "-"},
                {"type": "text", "text": "-"}
    ]

        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": TEMPLATE_NAME,
                "language": {"code": "en_US"},
                "components": [
                    {
                        "type": "body",
                        "parameters": parameters
                    }
                ]
            }
        }

        # Send request
        r = requests.post(url, headers=headers, json=payload)
        r.raise_for_status()
        print(f"[META] ✅ Template sent to {to_number}")

    except Exception as e:
        print(f"[META ERROR] ❌ {e}")

# Format Catalog Order JSON
def format_order_json(order_data):
    """
    Format WhatsApp catalog order using correct names and prices from the saved CSV.
    """
    try:
        product_items = order_data.get("product_items", [])
        output = ["* Items:"]
        unknown_items = []
        total = 0

        if not product_items:
            return "⚠️ No items found in the order."

        for item in product_items:
            retailer_id = item.get("product_retailer_id")
            quantity = item.get("quantity", 1)

            catalog_item = catalog_lookup.get(retailer_id)
            if catalog_item:
                name = catalog_item["name"]
                price = catalog_item["price"]
                currency = catalog_item["currency"]
                line_total = quantity * price
                total += line_total

                output.append(f"- {quantity} x {name} - LBP{line_total}")
            else:
                unknown_items.append(retailer_id)

        if total:
            output.append(f"\n* Total Price: {total} LBP")

        if unknown_items:
            output.append(f"\n⚠️ Some items were not found in our menu: {', '.join(unknown_items)}")

        return "\n".join(output)

    except Exception as e:
        print(f"[ORDER FORMAT ERROR] {e}")
        return "🛒 Order received, but couldn't be parsed properly."


def extract_items_from_summary(summary_text):
    """
    Parse items from AI summary text and build a clean items list.
    Supports multiple modifications separated by commas.
    """
    items = []
    lines = summary_text.splitlines()
    inside_items = False

    for line in lines:
        line = line.strip()
        if line.startswith("* Items:"):
            inside_items = True
            continue

        if inside_items:
            if not line.startswith("-"):
                break  # End of items section

            # Example match: "- 2 x Tawouk (No pickles, Extra fries)"
            match = re.match(r"- (\d+) x (.+?)(?: \((.+?)\))?$", line)
            if match:
                quantity = int(match.group(1))
                item_name = match.group(2).strip()
                modifications_raw = match.group(3)

                modifications = []
                if modifications_raw and modifications_raw.lower() != "no modifications":
                    # Split modifications safely by commas
                    modifications = [mod.strip() for mod in modifications_raw.split(",") if mod.strip()]

                items.append({
                    "name": item_name,
                    "quantity": quantity,
                    "modifications": modifications
                })

    return items


# Main Webhook Handler
@app.route('/webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        # ✅ Verify webhook
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == META_VERIFY_TOKEN:
                print("[WEBHOOK] ✅ Verification successful")
                return challenge, 200
            else:
                print("[WEBHOOK] ❌ Verification failed")
                return "Verification failed", 403

    if request.method == 'POST':
        data = request.json
        try:
            entry = data.get('entry', [])[0]
            change = entry.get('changes', [])[0]
            value = change.get('value', {})

            messages = value.get('messages', [])
            contacts = value.get('contacts', [])

            if not messages:
                return "OK", 200

            msg = messages[0]
            from_number = msg.get('from')  # e.g., '96181234567'
            message_type = msg.get('type')  # 'text', 'image', 'audio', 'button', etc.
            incoming_msg = ''
            username = contacts[0]['profile']['name'] if contacts else None

            # Handle different types
            if message_type == 'text':
                incoming_msg = msg.get('text', {}).get('body', '').strip()
            elif message_type == 'audio':
                audio_id = msg.get('audio', {}).get('id')
                if audio_id:
                    audio_url = get_media_url_from_meta(audio_id)
                    if audio_url:
                        incoming_msg = transcribe_audio_from_url(audio_url)
                    else:
                        incoming_msg = "⚠️ Failed to download audio. Please type your message."
            elif message_type == 'order':
                order_json = msg.get('order', {})
                incoming_msg = format_order_json(order_json)
            elif message_type == 'button':
                incoming_msg = msg.get('button', {}).get('text', '')
            elif message_type == 'interactive':
                interactive = msg.get('interactive', {})
                incoming_msg = interactive.get('button_reply', {}).get('title') or interactive.get('list_reply', {}).get('title')
            else:
                incoming_msg = f"[Unsupported {message_type} message]"

            print(f"[DEBUG] From: {from_number}")
            print(f"[DEBUG] Username: {username}")
            print(f"[DEBUG] MessageType: {message_type}")
            print(f"[DEBUG] Body: {incoming_msg}")

            # Log and process
            customer_id = database.upsert_customer(from_number, username)
            conversation_id = database.get_or_create_conversation(customer_id) if customer_id else None
            history = database.get_conversation_history(conversation_id) if conversation_id else []

            if customer_id:
                database.log_message(customer_id, incoming_msg, direction="incoming", conversation_id=conversation_id)

            current_time = time.time()
            user_cache = recent_messages_cache[from_number]

            # Merge logic
            if current_time - user_cache["last_message_time"] < MERGE_TIMEOUT_SECONDS:
                user_cache["buffer"].append(incoming_msg)
                user_cache["last_message_time"] = current_time
                print(f"[MERGE] Buffered message for {from_number}. Waiting for more...")
                return "OK", 200
            else:
                # Send full message buffer to AI
                user_cache["buffer"].append(incoming_msg)
                merged_message = " ".join(user_cache["buffer"]).strip()
                print(f"[MERGE] Merged message: {merged_message}")
                
                # Clear buffer
                user_cache["buffer"] = []
                user_cache["last_message_time"] = current_time

                response_text, _ = process_message(merged_message, history, customer_id)

            print(f"[DEBUG] AI Response: {response_text}")

            if customer_id and response_text:
                database.log_message(customer_id, response_text, direction="outgoing", conversation_id=conversation_id)
                if "[ORDER_SUMMARY]" in response_text:
                    print("[DEBUG] [ORDER_SUMMARY] detected, sending template instead.")
                    summary_text = response_text.split("[ORDER_SUMMARY]")[0].strip()
                    send_template_via_meta(from_number, summary_text)
                    # 🚀 BUILD order context if missing
                    if customer_id not in user_order_context or not user_order_context[customer_id].get("items"):
                        

                        delivery_type = "takeaway" if "Pickup Branch" in summary_text else "delivery"
                        total_price_match = re.search(r"\* Total Price:\s*(?:LBP)?\s*([\d,]+)", summary_text)
                        address_match = re.search(r"\* Delivery Address: (.+)", summary_text)
                        branch_match = re.search(r"\* Pickup Branch: (.+)", summary_text)
                        phone_match = re.search(r"\* Contact Phone: (.+)", summary_text)
                        name_match = re.search(r"\* Customer Name: (.+)", summary_text)
                        extracted_items = extract_items_from_summary(summary_text)
                        
                        user_order_context[customer_id] = {
                            "delivery_type": delivery_type,
                            "items": extracted_items,  # No clean way to extract from text here, leave empty
                            "price": int(total_price_match.group(1).replace(",", "")) if total_price_match else None,
                            "address": address_match.group(1).strip() if address_match else None,
                            "phone": phone_match.group(1).strip() if phone_match else from_number,
                            "branch": branch_match.group(1).strip() if branch_match else None,
                            "name": name_match.group(1).strip() if name_match else None,
                            "confirmed": False,
                        }
                        print(f"[DEBUG] 🛒 Built temporary order context for customer {customer_id}")
                # elif "[ORDER_CONFIRMED]" in response_text:
                #     print("[DEBUG] [ORDER_CONFIRMED] detected, sending template instead.")
                #     # summary_text = response_text.split("[ORDER_CONFIRMED]")[0].strip()
                #     # send_template_via_meta(from_number, summary_text)
                #     return "OK", 200

                else:
                    # If neither ORDER_SUMMARY nor ORDER_CONFIRMED is present, send normal text
                    send_text_via_meta(from_number, response_text)

            # ✅ If it's a button click and it's "Confirm"
            if message_type == "button" and incoming_msg.lower() == "confirm":
                customer_id = database.get_customer_id_by_phone(from_number)
                if customer_id:
                    if customer_id in user_order_context:
                        print(f"Order context: {user_order_context[customer_id]}")  # Debug
                        user_order_context[customer_id]["confirmed"] = True  # ✅ Force confirmed
                        result = confirm_order(customer_id)
                        print(f"[CONFIRMATION RESULT] {result}")
                        send_text_via_meta(from_number, "✅ Thank you! Your order has been confirmed. We'll begin preparing it right away.")
                        user_order_context.pop(customer_id, None)  # ✅ Clean after save
                    else:
                        send_text_via_meta(from_number, "⚠️ No pending order found to confirm.")


            return "OK", 200

        except Exception as e:
            print(f"[ERROR] Webhook processing failed: {e}")
            return "ERROR", 500


if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=8000)

