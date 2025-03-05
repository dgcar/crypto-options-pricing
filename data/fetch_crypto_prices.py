"""
Fetches and stores historical spot prices for cryptocurrencies.

This script retrieves real-time cryptocurrency spot prices and saves them to a PostgreSQL database.
The data is later used for options pricing models, including Black-Scholes and Heston stochastic volatility.

Key Features:
- Fetches price data including open, high, low, close, and volume.
- Ensures all required columns are present.
- Converts timestamps to UTC format.
- Stores the processed data in a PostgreSQL database.

This is part of a larger project that compares Black-Scholes and Heston models for pricing cryptocurrency options.
"""

import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from datetime import datetime, timezone

# Database connection settings (Replace placeholders with actual credentials)
DB_NAME = "your_database"
DB_USER = "your_username"
DB_PASSWORD = "your_password"
DB_HOST = "your_host"
DB_PORT = "5432"

# Create database connection
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def store_spot_prices(df, engine):
    print("✅ Storing crypto prices in the database...")

    # Ensure required columns exist
    required_columns = {"crypto_id", "symbol", "timestamp", "open", "high", "low", "close", "volume"}
    missing_columns = required_columns - set(df.columns)
    for col in missing_columns:
        df[col] = None  # Add missing columns with default None

    # Handle missing values
    df = df.copy()  # Avoid chained assignment warnings
    df["open"].fillna(df["close"], inplace=True)
    df["high"].fillna(df["close"], inplace=True)
    df["low"].fillna(df["close"], inplace=True)
    df["volume"].fillna(0, inplace=True)

    # Ensure timestamp is in correct format
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s").dt.tz_localize("UTC")

    # Store in the database
    df.to_sql("crypto_prices", con=engine, if_exists="append", index=False)
    print("✅ Crypto prices stored successfully!")

# Example dataframe (Replace with actual data fetching logic)
data = {
    "crypto_id": [1, 2],
    "symbol": ["BTC", "ETH"],
    "timestamp": [datetime.now(timezone.utc).timestamp()] * 2,
    "open": [96359.0, 2769.1],
    "high": [96359.0, 2769.1],
    "low": [96359.0, 2769.1],
    "close": [96359.0, 2769.1],
    "volume": [None, None]  # These will be set to 0
}

spot_df = pd.DataFrame(data)
store_spot_prices(spot_df, engine)
