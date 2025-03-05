"""
Fetches available cryptocurrency option contracts and real-time market prices from Deribit.

This script retrieves a list of active options from Deribit, along with their real-time market prices and implied volatility.
The data is then stored in a PostgreSQL database for further analysis in options pricing models like Black-Scholes and Heston.

Key Features:
- Fetches available option contracts (instrument names, expiration dates, strike prices, option types).
- Retrieves real-time market prices and implied volatility from Deribit.
- Cleans and merges data, ensuring only relevant options with prices are stored.
- Clears old Deribit data before inserting fresh values.
- Stores the processed data in a PostgreSQL database.

This script is part of a broader project that evaluates the accuracy of Black-Scholes and Heston models in pricing cryptocurrency options.
"""

import requests
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text

# Database connection settings (Replace placeholders with actual credentials)
DB_NAME = "your_database"
DB_USER = "your_username"
DB_PASSWORD = "your_password"
DB_HOST = "your_host"
DB_PORT = "5432"

# Deribit API Endpoints
DERIBIT_INSTRUMENTS_API = "https://www.deribit.com/api/v2/public/get_instruments"
DERIBIT_PRICES_API = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"

# Cryptocurrencies to track
CRYPTO_MAPPING = {
    "BTC": 1,
    "ETH": 2
}

# Fetch available option contracts (instruments)
def fetch_available_instruments(currency="BTC"):
    params = {"currency": currency, "kind": "option", "expired": "false"}
    response = requests.get(DERIBIT_INSTRUMENTS_API, params=params)

    if response.status_code == 200:
        instruments = response.json().get("result", [])
        df = pd.DataFrame(instruments)

        if not df.empty:
            df = df.rename(columns={"strike": "strike_price"})  # ✅ Rename correctly
            df = df[["instrument_name", "expiration_timestamp", "strike_price", "option_type", "base_currency"]]
            df["expiration_date"] = df["expiration_timestamp"].astype("int64") // 1000  # Convert to seconds
            return df
        else:
            print(f"⚠️ No instruments found for {currency}.")
            return None
    else:
        print(f"❌ Error fetching instruments for {currency}: {response.status_code}")
        return None

# Fetch real-time market prices for options
def fetch_deribit_prices(currency="BTC"):
    params = {"currency": currency, "kind": "option"}
    response = requests.get(DERIBIT_PRICES_API, params=params)

    if response.status_code == 200:
        data = response.json().get("result", [])
        df = pd.DataFrame(data)

        if not df.empty:
            df = df.rename(columns={"bid_price": "real_market_price"})
            df["implied_volatility"] = df["mark_iv"] / 100  # ✅ Convert IV from percentage to decimal
            df = df[["instrument_name", "real_market_price", "implied_volatility"]]
            return df
        else:
            print(f"⚠️ No prices found for {currency}.")
            return None
    else:
        print(f"❌ Error fetching prices for {currency}: {response.status_code}")
        return None


# Create PostgreSQL connection
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Clear old data before inserting new data
def clear_old_deribit_data(engine):
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM deribit_options;"))
        connection.commit()
        print("✅ Old Deribit options data cleared.")

# Store fetched options in the database
def store_deribit_options(df, engine):
    if df is not None and not df.empty:
        df = df[["crypto_id", "symbol", "strike_price", "option_type", "expiration_date", "real_market_price", "implied_volatility", "instrument_name"]]
        df.to_sql("deribit_options", con=engine, if_exists="append", index=False)
        print(f"✅ Inserted {len(df)} rows into deribit_options table.")
    else:
        print("⚠️ No data to insert.")

# Run the process
clear_old_deribit_data(engine)

for currency in CRYPTO_MAPPING.keys():
    df_instruments = fetch_available_instruments(currency)
    df_prices = fetch_deribit_prices(currency)

    if df_instruments is not None and df_prices is not None:
        # Merge instruments with prices on instrument_name
        merged_df = pd.merge(df_instruments, df_prices, on="instrument_name", how="left")
        merged_df["crypto_id"] = CRYPTO_MAPPING[currency]
        merged_df["symbol"] = currency
        merged_df = merged_df.dropna(subset=["real_market_price"])  # Drop missing prices

        store_deribit_options(merged_df, engine)

print("✅ Deribit options fetching and storage complete.")
