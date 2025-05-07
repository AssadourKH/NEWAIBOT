# # core/core.py

import os
import json
import pandas as pd
import time
import logging
from datetime import datetime
import requests
from core.openai_client import get_chat_completion
from utils import database
from core.constants import get_system_prompt
import re
import copy

# Configure logging
logging.basicConfig(level=logging.INFO)

# Meta API credentials
META_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
META_API_VERSION = "v22.0"
TEMPLATE_NAME = "order_confirmation"

# Load the menu CSV file
try:
    menu_df = pd.read_csv("final_catalog_match.csv")
except Exception as e:
    logging.error(f"Error loading menu CSV: {e}")
    menu_df = pd.DataFrame()

# Cache to throttle duplicate/rapid messages
last_message_cache = {}

# Per-customer order context memory
user_order_context = {}

def recalculate_price(order_items, catalog):
    total = 0
    for item in order_items:
        item_id = item.get("id")
        item_name = item.get("name", "").lower()
        quantity = item.get("quantity", 1)

        catalog_item = None

        # Try ID match
        if item_id:
            catalog_item = next((c for c in catalog if c.get("retailer_id") == item_id), None)

        # Fallback to name match (partial, case-insensitive)
        if not catalog_item:
            catalog_item = next(
                (c for c in catalog if item_name in c.get("name", "").lower()), None
            )

        if catalog_item:
            try:
                price = int(str(catalog_item.get("price", "0")).replace(",", "").strip())
                total += quantity * price
            except ValueError:
                print(f"[WARNING] Failed to parse price for item: {catalog_item}")

    return total


def send_whatsapp_template(to_number, summary):
    """
    Send a WhatsApp template via Meta Cloud API.
    """
    url = f"https://graph.facebook.com/{META_API_VERSION}/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }
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
                    "parameters": [
                        {"type": "text", "text": summary}
                    ]
                }
            ]
        }
    }
    try:
        print("[META] Payload:", json.dumps(payload, indent=2))
        response = requests.post(url, headers=headers, json=payload)
        print("[META] Response:", response.status_code, response.text)
        response.raise_for_status()
        print(f"[META] ✅ Template sent to {to_number}")
    except Exception as e:
        print(f"[META ERROR] ❌ Failed to send template: {e}")

def get_order_summary(context):
    """
    Generate a WhatsApp-style order summary from the order_context dictionary.
    """
    summary_lines = []

    # Heading based on delivery type
    if context.get("delivery_type") == "delivery":
        summary_lines.append("✅ Your order has been confirmed! Here are your final details:")
    else:
        summary_lines.append("✅ Your order is ready for pickup! Here are your details:")

    # Items
    summary_lines.append("* Items:")
    for item in context.get("items", []):
        name = item.get("name", "Unknown Item")
        qty = item.get("quantity", 1)
        mods = item.get("modifications", [])
        if mods:
            summary_lines.append(f"  - {qty} x {name} ({', '.join(mods)})")
        else:
            summary_lines.append(f"  - {qty} x {name}")

    # Total price
    if "price" in context:
        summary_lines.append(f"* Total Price: {context['price']} LBP")

    # Delivery or pickup info
    if context.get("delivery_type") == "delivery":
        summary_lines.append(f"* Delivery Address: {context.get('address', 'N/A')}")
        summary_lines.append(f"* Contact Phone: {context.get('phone', 'N/A')}")
    else:
        summary_lines.append(f"* Pickup Branch: {context.get('branch', 'N/A')}")
        summary_lines.append(f"* Customer Name: {context.get('name', 'N/A')}")

    summary_lines.append("* [ORDER_CONFIRMED]")

    return "\n".join(summary_lines)

def process_message(user_input, history, customer_id):
    """
    Process incoming messages and manage order workflows.
    """
    cache_key = str(customer_id)

    order_context = user_order_context.get(customer_id, {
        "delivery_type": None,
        "address": None,
        "phone": None,
        "name": None,
        "branch": None,
        "items": [],
        "confirmed": False
    })

    current_time = time.time()
    last_entry = last_message_cache.get(cache_key)
    is_short = len(user_input.strip()) <= 10

    # Throttle repeated/rapid messages
    if last_entry:
        last_msg, last_time = last_entry
        time_diff = current_time - last_time
        if (user_input.strip().lower() == last_msg and time_diff < 10) or (is_short and time_diff < 4):
            logging.info(f"[SKIP] Throttled message from {customer_id}: '{user_input}' ({int(time_diff)}s apart)")
            return "", history

    last_message_cache[cache_key] = (user_input.strip().lower(), current_time)

    # Fetch branch data
    try:
        branches = database.execute_query('SELECT name, location, delivery_time FROM [dbo].[branches]')
    except Exception as e:
        logging.error(f"[DB ERROR] {e}")
        branches = []
    
    branch_info = "\n".join(f"- {row[0]}: {row[1]} (Delivery: {row[2]})" for row in branches)
    recent_history = history[-50:] if len(history) > 50 else history
    catalog_items = menu_df.to_dict(orient="records")

    system_prompt = get_system_prompt(customer_id, recent_history, catalog_items, branch_info)

    messages = recent_history + [system_prompt, {"role": "user", "content": user_input}]

    try:
        response = get_chat_completion(messages)
    except Exception as e:
        logging.error(f"[ERROR] OpenAI chat completion failed:\n{e}")
        return "Sorry, I couldn't process your request at the moment.", history
    
    history.append({"role": "assistant", "content": response})

    # Detect if AI returned JSON
    json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if json_match:
        try:
            order_data = json.loads(json_match.group())

            if order_data.get("undo") is True and order_context.get("history"):
                order_context["items"] = order_context["history"].pop()
                order_context["price"] = recalculate_price(order_context["items"], catalog_items)
                summary = get_order_summary(order_context)
                history.append({"role": "assistant", "content": f"↩️ Last change undone:\n\n{summary}"})
                user_order_context[customer_id] = order_context
                return summary, history

            if order_data.get("modification") is True:
                if order_context.get("confirmed"):
                    history.append({"role": "assistant", "content": "❌ Sorry, the order has already been confirmed and can no longer be modified."})
                    return "Order is locked.", history

                for change in order_data.get("changes", []):
                    item_id = change.get("item_id")
                    if not item_id:
                        continue

                    order_context.setdefault("history", []).append(copy.deepcopy(order_context["items"]))

                    if change["type"] == "remove_item":
                        order_context["items"] = [i for i in order_context["items"] if i.get("id") != item_id]
                    else:
                        for item in order_context["items"]:
                            if item.get("id") == item_id:
                                if change["type"] == "quantity":
                                    item["quantity"] = change.get("new_quantity", item["quantity"])
                                elif change["type"] == "add_modification":
                                    item.setdefault("modifications", []).append(change["mod"])
                                elif change["type"] == "remove_modification":
                                    if "modifications" in item and change["mod"] in item["modifications"]:
                                        item["modifications"].remove(change["mod"])

                order_context["price"] = recalculate_price(order_context["items"], catalog_items)
                summary = get_order_summary(order_context)
                history.append({"role": "assistant", "content": f"✅ Order updated:\n\n{summary}"})
                user_order_context[customer_id] = order_context
                return summary, history

            price = order_data.get("price")
            # Fallback: try to parse price from text response if price still missing
            if price is None:
                # Try recalculation first
                price = recalculate_price(order_data.get("items", []), catalog_items)

                # If still None or 0, extract from text
                if not price:
                    match = re.search(r"\* Total Price:\s*(?:LBP)?\s*([\d,]+)", response)
                    if match:
                        try:
                            price = int(match.group(1).replace(",", ""))
                        except:
                            price = None

            # Final confirmed order
            order_context.update({
                "delivery_type": order_data.get("type"),
                "items": order_data.get("items", []),
                "address": order_data.get("address"),
                "phone": order_data.get("phone"),
                "branch": order_data.get("branch"),
                "name": order_data.get("name"),
                "confirmed": True,
                "price": price,
            })


            # Send WhatsApp template
            customer_number = database.get_phone_by_customer_id(customer_id)
            final_summary = get_order_summary(order_context)
            if customer_number:
                send_whatsapp_template(customer_number, final_summary)

        except Exception as e:
            logging.error(f"[JSON PARSE ERROR] Couldn't extract order: {e}")

    user_order_context[customer_id] = order_context

    return response, history

def confirm_order(customer_id):
    """
    Save confirmed order to database.
    """
    order_context = user_order_context.get(customer_id)
    print("Order context:", order_context)
    if not order_context or not order_context.get("confirmed"):
        return "No confirmed order to save."

    database.insert_order(
        customer_id=customer_id,
        order_type=order_context["delivery_type"],
        items=json.dumps(order_context["items"]),
        total_price=order_context["price"],
        address=order_context["address"],
        phone=order_context["phone"],
        branch=order_context["branch"],
        customer_name=order_context["name"]
    )
    return "✅ Order saved to database."
