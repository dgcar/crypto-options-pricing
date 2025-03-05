"""
Visualizes Heston model option pricing against real market prices.

This script retrieves calculated Heston model prices and real market option prices from the database,
merges the data, and generates a scatter plot to compare the pricing models.

Key Features:
- Fetches Heston model-calculated option prices from the database.
- Fetches real market option prices from Deribit for comparison.
- Retrieves latest spot prices to scale the market data dynamically.
- Merges and filters data to ensure accurate comparison.
- Generates a scatter plot comparing Heston model prices to real market prices.

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

# Fetch Heston model-calculated data
query_heston = """
    SELECT c.symbol, o.instrument_name, o.strike_price, o.option_type, 
           o.expiration_date, o.heston_price
    FROM crypto_options o
    JOIN cryptocurrencies c ON o.crypto_id = c.crypto_id
    WHERE o.heston_price IS NOT NULL
    LIMIT 1000
"""
df_heston = pd.read_sql(query_heston, con=engine)

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

if df_heston.empty or df_real_deribit.empty or df_spot_prices.empty:
    print("❌ ERROR: No data available! Ensure the database is populated before running visualization.")
    exit()

# Convert expiration_date from milliseconds to seconds
current_time = int(datetime.utcnow().timestamp())
df_heston["expiration_date"] = df_heston["expiration_date"] // 1000
df_real_deribit["expiration_date"] = df_real_deribit["expiration_date"] // 1000

# Compute time-to-expiration for Heston data
df_heston["T"] = (df_heston["expiration_date"] - current_time) / (365 * 24 * 60 * 60)
df_heston["T"] = df_heston["T"].clip(lower=0.01)

# Ensure correct data types
df_heston["strike_price"] = df_heston["strike_price"].astype(float)
df_real_deribit["strike_price"] = df_real_deribit["strike_price"].astype(float)
df_heston["option_type"] = df_heston["option_type"].str.lower()
df_real_deribit["option_type"] = df_real_deribit["option_type"].str.lower()

# Merge Heston and real market datasets on symbol, strike price, and option type
tolerance = 3 * 60 * 60  # 3 hours in seconds
merged_df = df_heston.merge(
    df_real_deribit, on=["symbol", "strike_price", "option_type"],
    suffixes=("_heston", "_real"), how="left"
)

# Filter merged rows with expiration dates within ±3 hours
merged_df = merged_df[abs(merged_df["expiration_date_heston"] - merged_df["expiration_date_real"]) <= tolerance]

# Merge spot prices into the dataframe for dynamic scaling of real market prices
merged_df = merged_df.merge(df_spot_prices, on="symbol", how="left")

# Scale real market prices dynamically based on the current spot price
merged_df["real_market_price"] = merged_df["real_market_price"] * merged_df["spot_price"]

print("Merged Data (Sample):")
print(merged_df.head())

if merged_df.empty:
    print("❌ ERROR: No matching data found for visualization!")
    exit()

# Filter out extreme Heston prices for clarity
merged_df = merged_df[(merged_df["heston_price"] > 1e-3) & (merged_df["heston_price"] < 1e6)]

print("Merged Data (First 10 rows):")
print(merged_df[["symbol", "strike_price", "option_type", "heston_price", "real_market_price"]].head(10))

# Analyze error in pricing model
merged_df["error"] = abs(merged_df["heston_price"] - merged_df["real_market_price"])
outliers = merged_df.sort_values(by="error", ascending=False).head(10)
print(outliers)

# Plot the comparison between Heston model prices and real market prices
plt.figure(figsize=(10, 5))
plt.scatter(merged_df["strike_price"], merged_df["heston_price"], color='green', label='Heston Price')
plt.scatter(merged_df["strike_price"], merged_df["real_market_price"], color='red', label='Real Market Price')
plt.xlabel("Strike Price")
plt.ylabel("Option Price")
plt.title("Heston vs Real Market Prices")
plt.yscale("log")  # Use log scale for better visualization
plt.legend()
plt.grid(True)
plt.show()
