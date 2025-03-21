import os
import json
import threading
import time
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
stock_list = list(set(nifty50_top5 + banknifty_top5))  # ✅ Remove duplicates

# ✅ Function to Fetch & Update Firestore Every 15 Minutes using Batch Writes
def update_stock_prices():
    while True:
        try:
            stock_data = {}
            tickers = " ".join(stock_list)  # ✅ Fetch all stocks in one request
            data = yf.download(tickers=tickers, period="1d", interval="1m", progress=False)

            if "Close" in data:
                close_prices = data["Close"].iloc[-1]  # ✅ Get latest close prices
                prev_closes = data["Close"].iloc[-2]  # ✅ Get previous close prices (1 min before)

                batch = db.batch()  # ✅ Start a Firestore batch write

                for ticker in stock_list:
                    if ticker in close_prices and ticker in prev_closes:
                        live_price = round(close_prices[ticker], 2)
                        prev_close = round(prev_closes[ticker], 2)
                        change = round(((live_price - prev_close) / prev_close) * 100, 2)

                        stock_data[ticker] = {
                            "price": live_price,
                            "change": change,
                            "prevClose": prev_close
                        }
                        doc_ref = db.collection("market_indices").document(ticker)
                        batch.set(doc_ref, stock_data[ticker])  # ✅ Batch update

                batch.commit()  # ✅ Execute batch write
                print("✅ Stock prices updated in Firestore:", stock_data)

            else:
                print("❌ No stock price data found!")

        except Exception as e:
            print("❌ Error updating stock prices:", str(e))

        time.sleep(900)  # ✅ Update every 15 minutes (900 seconds)

# ✅ Start Background Thread
threading.Thread(target=update_stock_prices, daemon=True).start()

@app.route('/')
def home():
    return "✅ Nifty & Bank Nifty Live Stock Price API is Running!"

@app.route('/nifty-bank-live')
def get_stock_prices():
    try:
        stock_prices = {}
        docs = db.collection("market_indices").get()

        for doc in docs:
            stock_prices[doc.id] = doc.to_dict()

        return jsonify(stock_prices)  # ✅ Returns all stored stock prices

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
