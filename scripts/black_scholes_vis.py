"""
Visualizes Black-Scholes option pricing against real market prices.

This script retrieves calculated Black-Scholes prices and real market option prices from the database,
merges the data, and generates a scatter plot to compare the pricing models.

Key Features:
- Fetches Black-Scholes calculated option prices from the database.
- Fetches real market option prices from Deribit for comparison.
- Retrieves latest spot prices to scale the market data dynamically.
- Merges and filters data to ensure accurate comparison.
- Generates a scatter plot comparing Black-Scholes prices to real market prices.

This script is part of a broader project that evaluates the accuracy of the Black-Scholes and Heston models for pricing cryptocurrency options.
"""

import pandas as pd
import numpy as np
import psycopg2
from sqlalchemy import create_engine, text
import matplotlib.pyplot as plt
from datetime import datetime

# Database connection settings (Replace placeholders with actual credentials)
DB_NAME = "your_database"
DB_USER = "your_username"
DB_PASSWORD = "your_password"
DB_HOST = "your_host"
DB_PORT = "5432"

# Create database connection
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Fetch Black-Scholes calculated data
query_black_scholes = """
    SELECT c.symbol, o.instrument_name, o.strike_price, o.option_type, 
           o.expiration_date, o.black_scholes_price
    FROM crypto_options o
    JOIN cryptocurrencies c ON o.crypto_id = c.crypto_id
    WHERE o.black_scholes_price IS NOT NULL
    LIMIT 1000
"""
df_black_scholes = pd.read_sql(query_black_scholes, con=engine)

# Fetch real market options data
query_real_deribit = """
    SELECT c.symbol, d.symbol AS option_symbol, d.strike_price, d.option_type, d.expiration_date, 
           d.real_market_price
    FROM deribit_options d
    JOIN cryptocurrencies c ON d.crypto_id = c.crypto_id
    WHERE d.real_market_price IS NOT NULL
    LIMIT 1000
"""
df_real_deribit = pd.read_sql(query_real_deribit, con=engine)

# Fetch latest spot prices for scaling
query_spot_prices = """
    SELECT c.symbol, p.close AS spot_price
    FROM crypto_prices p
    JOIN cryptocurrencies c ON p.crypto_id = c.crypto_id
    ORDER BY p.timestamp DESC
    LIMIT 2  -- Get the latest BTC & ETH prices
"""
df_spot_prices = pd.read_sql(query_spot_prices, con=engine)

if df_black_scholes.empty or df_real_deribit.empty or df_spot_prices.empty:
    print("❌ ERROR: No data available! Ensure the database is populated before running visualization.")
    exit()

# Convert expiration_date to seconds
current_time = int(datetime.utcnow().timestamp())  # Get current timestamp
df_black_scholes["expiration_date"] = df_black_scholes["expiration_date"] // 1000
df_real_deribit["expiration_date"] = df_real_deribit["expiration_date"] // 1000

# Convert to datetime and compute time to expiration
df_black_scholes["T"] = (df_black_scholes["expiration_date"] - current_time) / (365 * 24 * 60 * 60)
df_black_scholes["T"] = df_black_scholes["T"].clip(lower=0.01)  # Prevent division by zero

# Assign implied volatility estimate
df_black_scholes["sigma"] = 0.3  # Default value if missing

# Ensure correct data types
df_black_scholes["strike_price"] = df_black_scholes["strike_price"].astype(float)
df_real_deribit["strike_price"] = df_real_deribit["strike_price"].astype(float)
df_black_scholes["option_type"] = df_black_scholes["option_type"].str.lower()
df_real_deribit["option_type"] = df_real_deribit["option_type"].str.lower()

# Merge datasets on strike price and option type with expiration date tolerance
tolerance = 3 * 60 * 60  # 3 hours in seconds
merged_df = df_black_scholes.merge(
    df_real_deribit, on=["symbol", "strike_price", "option_type"], suffixes=("_bs", "_real"), how="left"
)

# Filter matches with expiration dates within ±3 hours
merged_df = merged_df[abs(merged_df["expiration_date_bs"] - merged_df["expiration_date_real"]) <= tolerance]

# Merge spot prices into the dataframe for dynamic scaling
merged_df = merged_df.merge(df_spot_prices, on="symbol", how="left")

# Scale real market prices dynamically based on the current spot price
merged_df["real_market_price"] = merged_df["real_market_price"] * merged_df["spot_price"]

print("Merged Data (Sample):")
print(merged_df.head())

if merged_df.empty:
    print("❌ ERROR: No matching data found for visualization!")
    exit()

# Filter out extreme Black-Scholes prices
merged_df = merged_df[(merged_df["black_scholes_price"] > 1e-3) & (merged_df["black_scholes_price"] < 1e6)]

print("Merged Data (First 10 rows):")
print(merged_df[["symbol", "strike_price", "option_type", "black_scholes_price", "real_market_price"]].head(10))

# Plot the comparison
plt.figure(figsize=(10, 5))
plt.scatter(merged_df["strike_price"], merged_df["black_scholes_price"], color='blue', label='Black-Scholes Price')
plt.scatter(merged_df["strike_price"], merged_df["real_market_price"], color='red', label='Real Market Price')
plt.xlabel("Strike Price")
plt.ylabel("Option Price")
plt.title("Black-Scholes vs Real Market Prices")
plt.yscale("log")  # Log scale for better comparison
plt.legend()
plt.grid()
plt.show()
