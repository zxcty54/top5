import os
import json
import threading
import time
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)

# ✅ Load Firebase credentials
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

try:
    if not firebase_credentials:
        raise ValueError("🚨 FIREBASE_CREDENTIALS is missing!")

    cred_dict = json.loads(firebase_credentials)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

except Exception as e:
    print(f"❌ Firebase Initialization Error: {e}")
    db = None  # Prevent further crashes

# ✅ Predefined Stocks
nifty50_top5 = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]
banknifty_top5 = ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS"]
stock_list = nifty50_top5 + banknifty_top5

# ✅ Function to Fetch & Update Firestore
def update_stock_prices():
    while True:
        if not db:  # ✅ Don't run if Firestore failed
            print("❌ Firestore not initialized. Skipping update.")
            time.sleep(15)
            continue

        try:
            stock_data = {}
            for ticker in stock_list:
                stock = yf.Ticker(ticker)
                try:
                    live_price = stock.fast_info["last_price"]
                    prev_close = stock.fast_info["previous_close"]
                    if prev_close:
                        change = ((live_price - prev_close) / prev_close) * 100
                        stock_data[ticker] = {
                            "price": round(live_price, 2),
                            "change": round(change, 2),
                            "prevClose": round(prev_close, 2)
                        }
                    else:
                        stock_data[ticker] = {"price": "N/A", "change": "N/A", "prevClose": "N/A"}
                except Exception:
                    stock_data[ticker] = {"price": "N/A", "change": "N/A", "prevClose": "N/A"}

            # ✅ Batch Firestore Updates
            batch = db.batch()
            for ticker, data in stock_data.items():
                doc_ref = db.collection("market_indices").document(ticker)
                batch.set(doc_ref, data)
            batch.commit()

            print("✅ Stock prices updated in Firestore:", stock_data)

        except Exception as e:
            print("❌ Error updating stock prices:", str(e))

        time.sleep(15)

# ✅ Function to Keep Render Alive
def keep_alive():
    while True:
        try:
            requests.get("https://your-api-url.onrender.com")  # Replace with your actual API URL
            print("✅ Pinged Render to stay awake")
        except Exception as e:
            print("❌ Ping Error:", str(e))

        time.sleep(45)  # Ping every 45 seconds

# ✅ Start Threads Only If Firestore Works
if db:
    threading.Thread(target=update_stock_prices, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()

@app.route('/')
def home():
    return jsonify({"message": "Nifty & Bank Nifty Live Stock Price API is Running!"})

@app.route('/nifty-bank-live')
def get_stock_prices():
    try:
        docs = db.collection("market_indices").stream()
        stock_prices = {doc.id: doc.to_dict() for doc in docs}
        return jsonify(stock_prices)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
