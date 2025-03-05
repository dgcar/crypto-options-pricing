"""
Fetches cryptocurrency options data and risk-free rates for pricing models.

This script retrieves real-time cryptocurrency options data from Deribit, along with the latest risk-free rate from FRED.
The data is stored in a PostgreSQL database for use in options pricing models, such as Black-Scholes and Heston stochastic volatility.

Key Features:
- Fetches options data (instrument name, expiration date, strike price, option type) for BTC and ETH.
- Retrieves the latest 10-year U.S. Treasury rate from FRED to serve as the risk-free rate.
- Stores collected data in a PostgreSQL database.

This script is part of a broader project that evaluates the accuracy of Black-Scholes and Heston models in pricing cryptocurrency options.
"""

import requests
import pandas as pd
import psycopg2
from sqlalchemy import create_engine

# Database connection settings (Replace placeholders with actual credentials)
DB_NAME = "your_database"
DB_USER = "your_username"
DB_PASSWORD = "your_password"
DB_HOST = "your_host"
DB_PORT = "5432"

# API Endpoints
DERIBIT_API_URL = "https://www.deribit.com/api/v2/public/get_instruments"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

# FRED API Key (Replace with your own or use publicly available data)
FRED_API_KEY = "your_fred_api_key"

# Cryptocurrencies to track
CRYPTO_MAPPING = {
    "BTC": 1,  # Matches the crypto_id in the cryptocurrencies table
    "ETH": 2
}

# Function to fetch options data from Deribit
def fetch_options_data(currency="BTC"):
    params = {"currency": currency, "kind": "option"}
    response = requests.get(DERIBIT_API_URL, params=params)
    
    if response.status_code == 200:
        data = response.json()["result"]
        df = pd.DataFrame(data)
        
        # Select relevant columns and rename
        df = df[["instrument_name", "expiration_timestamp", "strike", "option_type"]]
        
        # Convert expiration timestamp from milliseconds to seconds
        df["expiration_timestamp"] = df["expiration_timestamp"] // 1000  
        
        # Add additional columns
        df["timestamp"] = pd.to_datetime("now")  # Use current timestamp
        df["crypto_id"] = CRYPTO_MAPPING[currency]
        
        df.rename(columns={
            "expiration_timestamp": "expiration_date",
            "strike": "strike_price",
            "option_type": "option_type"
        }, inplace=True)
        
        return df
    else:
        print(f"❌ Error fetching options data for {currency}: {response.status_code}")
        return None

# Function to fetch risk-free rate from FRED
def fetch_risk_free_rate():
    params = {"series_id": "DGS10", "api_key": FRED_API_KEY, "file_type": "json"}
    response = requests.get(FRED_API_URL, params=params)
    
    if response.status_code == 200:
        data = response.json()["observations"]
        latest_rate = float(data[-1]["value"]) / 100  # Convert to decimal
        return latest_rate
    else:
        print(f"❌ Error fetching risk-free rate: {response.status_code}")
        return None

# Function to store options data in PostgreSQL
def store_options_to_db(df, engine):
    if df is not None and not df.empty:
        df.to_sql("crypto_options", con=engine, if_exists="append", index=False)
        print(f"✅ Inserted {len(df)} rows into crypto_options table.")
    else:
        print("⚠️ No data to insert.")

# Create PostgreSQL connection
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Fetch and store options data for BTC and ETH
for currency in CRYPTO_MAPPING.keys():
    df = fetch_options_data(currency)
    if df is not None:
        store_options_to_db(df, engine)

# Fetch risk-free rate and print it
risk_free_rate = fetch_risk_free_rate()
if risk_free_rate is not None:
    print(f"📈 Latest risk-free rate: {risk_free_rate}")

print("✅ Options data fetching and storage complete.")
