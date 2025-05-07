#core/catalog.py

import os
import requests
import csv
from dotenv import load_dotenv
import json
import re


load_dotenv()

# Facebook Catalog config
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
FB_CATALOG_ID = os.getenv("FB_CATALOG_ID")
OUTPUT_CSV_PATH = "final_catalog_match.csv"

print(f"[Catalog] FB_CATALOG_ID: {FB_CATALOG_ID}")
 
def get_catalog_items():
    """
    Fetch catalog products from Facebook Commerce API and save directly to CSV.
    """
    url = f"https://graph.facebook.com/v22.0/{FB_CATALOG_ID}/products"
    params = {
        "access_token": FB_ACCESS_TOKEN,
        "fields": "name,price,description,image_url,retailer_id"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        items = data.get("data", [])
        
     
        print(f"[Catalog] Retrieved {len(items)} items.")

        with open(OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                "retailer_id", "name", "description", "price", "currency", "image_url"
            ])
            writer.writeheader()

            for item in items:
                price_str = item.get("price", "")
                currency = "LBP"
                amount = ""

                # New: support format like "LBP500,000.00"
                if price_str and isinstance(price_str, str):
                    # Remove "LBP" prefix and commas safely
                    match = re.match(r"([A-Z]+)([\d,\.]+)", price_str)
                    if match:
                        currency = match.group(1)
                        raw_amount = match.group(2).replace(",", "").split(".")[0]
                        amount = raw_amount

                writer.writerow({
                    "retailer_id": item.get("retailer_id", ""),
                    "name": item.get("name", ""),
                    "description": item.get("description", ""),
                    "price": amount,
                    "currency": currency,
                    "image_url": item.get("image_url", "")
                })

        print(f"[Catalog] ✅ Saved to {OUTPUT_CSV_PATH}")

    except Exception as e:
        print(f"[Catalog Error] Failed to fetch catalog: {e}")


get_catalog_items()

# def build_catalog_lookup():
#     """
#     Build a lookup dict {retailer_id: item_name} and export to CSV.
#     """
#     catalog_items = get_catalog_items()
#     if not catalog_items:
#         print("[Catalog] No items retrieved from Facebook API.")
#         return {}

#     lookup = {
#         item["retailer_id"]: item["name"]
#         for item in catalog_items
#         if item.get("retailer_id") and item.get("name")
#     }

#     try:
#         with open(LOOKUP_CSV_OUTPUT, mode="w", encoding="utf-8", newline="") as csvfile:
#             writer = csv.writer(csvfile)
#             writer.writerow(["Retailer ID", "Item Name"])
#             for rid, name in lookup.items():
#                 writer.writerow([rid, name])
#         print(f"[Catalog] Lookup saved to {LOOKUP_CSV_OUTPUT}.")
#     except Exception as e:
#         print(f"[Catalog Error] Failed to write lookup CSV: {e}")

#     return lookup

# def match_catalog_with_menu_smart():
#     """
#     Combine Name + Size to match with catalog_lookup.csv.
#     Output: final_catalog_match.csv with Retailer ID + full menu row.
#     """
#     lookup = {}
#     try:
#         with open(LOOKUP_CSV_OUTPUT, mode="r", encoding="utf-8") as f:
#             reader = csv.DictReader(f)
#             for row in reader:
#                 retailer_id = row["Retailer ID"].strip()
#                 item_name = row["Item Name"].strip()
#                 lookup[item_name] = retailer_id
#     except Exception as e:
#         print(f"[Error] Failed to read {LOOKUP_CSV_OUTPUT}: {e}")
#         return

#     try:
#         with open(MENU_CSV_PATH, mode="r", encoding="utf-8") as menu_file, \
#              open("final_catalog_match.csv", mode="w", encoding="utf-8", newline="") as out_file:

#             reader = csv.DictReader(menu_file)
#             fieldnames = ["Retailer ID"] + reader.fieldnames
#             writer = csv.DictWriter(out_file, fieldnames=fieldnames)
#             writer.writeheader()

#             matched, unmatched = 0, 0

#             for row in reader:
#                 name = row["Name (English)"].strip()
#                 size = row["Size"].strip()
#                 combined_name = f"{name} {size}".strip()

#                 # Try full name with size first
#                 retailer_id = lookup.get(combined_name)

#                 # If not found, try name only
#                 if not retailer_id:
#                     retailer_id = lookup.get(name)

#                 if retailer_id:
#                     row["Retailer ID"] = retailer_id
#                     writer.writerow(row)
#                     matched += 1
#                 else:
#                     unmatched += 1
#                     print(f"[Unmatched] {combined_name} / {name} not found in catalog.")


#             print(f"[✅ Match Complete] {matched} matched, {unmatched} unmatched.")
#             print("[Output] Saved to final_catalog_match.csv")

#     except Exception as e:
#         print(f"[Error] Failed to process files: {e}")

#     return
   