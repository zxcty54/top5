import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)

# ✅ Load Firebase credentials from Render environment variable
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if firebase_credentials:
    cred_dict = json.loads(firebase_credentials)  # ✅ Convert string to JSON
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    raise ValueError("🚨 FIREBASE_CREDENTIALS environment variable is missing!")

# ✅ Predefined Stocks (Fixed List)
nifty50_top5 = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]
banknifty_top5 = ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS"]

@app.route('/')
def home():
    return "✅ Nifty & Bank Nifty Live Stock Price API is Running!"

@app.route('/update-stock-prices')
def update_stock_prices():
    try:
        stock_list = nifty50_top5 + banknifty_top5  # ✅ Merge both lists

        stock_data = {}

        for ticker in stock_list:
            stock = yf.Ticker(ticker)
            try:
                live_price = stock.fast_info["last_price"]
                prev_close = stock.fast_info["previous_close"]

                if prev_close:  # Ensure previous close is available
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

            # ✅ Update Firestore with stock price data
            db.collection("market_indices").document(ticker).set(stock_data[ticker])

        return jsonify({"message": "✅ Stock prices updated successfully", "data": stock_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/nifty-bank-live')
def get_stock_prices():
    try:
        # ✅ Fetch updated stock prices from Firestore
        docs = db.collection("market_indices").stream()
        stock_prices = {doc.id: doc.to_dict() for doc in docs}

        return jsonify(stock_prices)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
