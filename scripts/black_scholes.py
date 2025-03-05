"""
Calculates Black-Scholes option prices and updates the database.

This script retrieves cryptocurrency options data from the database, computes theoretical option prices using the Black-Scholes model, 
and updates the database with the calculated values.

Key Features:
- Fetches relevant options data including spot price, strike price, expiration date, and implied volatility.
- Converts expiration timestamps to time-to-expiry (T) in years.
- Applies the Black-Scholes formula to compute theoretical option prices.
- Logs detailed calculation steps for debugging.
- Updates the PostgreSQL database with Black-Scholes prices for each option.

This script is part of a broader project that compares Black-Scholes and Heston models for pricing cryptocurrency options.
"""

import pandas as pd
import numpy as np
import psycopg2
from sqlalchemy import create_engine, text
from scipy.stats import norm

# Database connection settings (Replace placeholders with actual credentials)
DB_NAME = "your_database"
DB_USER = "your_username"
DB_PASSWORD = "your_password"
DB_HOST = "your_host"
DB_PORT = "5432"

# Create database connection
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Black-Scholes Function
def black_scholes(S, K, T, r, sigma, option_type):
    """Compute Black-Scholes option price."""
    try:
        if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
            return None  # Invalid values

        log_term = np.log(S / K)
        sigma_sqrt_T = sigma * np.sqrt(T)

        if sigma_sqrt_T <= 0:
            return None  # Prevent division error

        d1 = (log_term + (r + 0.5 * sigma**2) * T) / sigma_sqrt_T
        d2 = d1 - sigma_sqrt_T

        # Ignore deep out-of-the-money (OTM) puts
        if option_type == "put" and norm.cdf(-d2) < 0.01:
            return 0  # Price too low to be meaningful

        if option_type == "call":
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        elif option_type == "put":
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        else:
            price = None

        return price
    except Exception:
        return None

# Fetch options data from database
query = """
    SELECT o.instrument_name, o.strike_price, o.expiration_date, o.option_type, cr.symbol, 
           p.close AS spot_price, d.implied_volatility
    FROM crypto_options o
    JOIN crypto_prices p ON o.crypto_id = p.crypto_id
    JOIN cryptocurrencies cr ON p.crypto_id = cr.crypto_id
    LEFT JOIN deribit_options d ON o.instrument_name = d.instrument_name
    ORDER BY p.timestamp DESC
"""
df = pd.read_sql(query, con=engine)

# Ensure there is data before proceeding
if df.empty:
    print("❌ ERROR: No data was fetched from the database!")
    exit()

# Constants
r = 0.045  # Risk-free rate (4.5%)

# Convert implied volatility from percentage to decimal
df["sigma"] = df["implied_volatility"].fillna(df["implied_volatility"].median())

# Convert expiration timestamps to datetime and compute `T` in years
df["expiration_date"] = pd.to_datetime(df["expiration_date"], unit="s")
current_time = pd.Timestamp.now()
df["time_to_expiry"] = (df["expiration_date"] - current_time).dt.total_seconds() / (365 * 24 * 60 * 60)

# Exclude options with less than 10 days to expiration
df = df[df["time_to_expiry"] > (14 / 365)]

# Remove extreme out-of-the-money options
df = df[df["strike_price"] < 1.5 * df["spot_price"]]

# Calculate Black-Scholes prices
df["black_scholes_price"] = df.apply(lambda row: black_scholes(
    row["spot_price"], row["strike_price"], row["time_to_expiry"], r, row["sigma"], row["option_type"]), axis=1
)

# Redirect detailed debugging output to a file
df_sample = df.sample(100)  # Pick 100 random samples for debugging
with open("black_scholes_log.txt", "w") as log_file:
    for index, row in df_sample.iterrows():
        S = row["spot_price"]
        K = row["strike_price"]
        T = row["time_to_expiry"]
        sigma = row["sigma"]
        option_type = row["option_type"]

        log_term = np.log(S / K)
        sigma_sqrt_T = sigma * np.sqrt(T)
        d1 = (log_term + (r + 0.5 * sigma**2) * T) / sigma_sqrt_T
        d2 = d1 - sigma_sqrt_T

        log_file.write(f"\n--- Black-Scholes Calculation for {row['instrument_name']} ---\n")
        log_file.write(f"Spot Price (S): {S}\n")
        log_file.write(f"Strike Price (K): {K}\n")
        log_file.write(f"Time to Expiry (T): {T} years\n")
        log_file.write(f"Implied Volatility (σ): {sigma}\n")
        log_file.write(f"d1: {d1}, d2: {d2}\n")
        log_file.write(f"BS Price: {row['black_scholes_price']}\n")

# Update the database with Black-Scholes prices
with engine.connect() as conn:
    trans = conn.begin()  # Start transaction
    for index, row in df.iterrows():
        if not np.isnan(row["black_scholes_price"]):  # Skip NaN values
            update_query = text("""
                UPDATE crypto_options
                SET black_scholes_price = :black_scholes_price
                WHERE instrument_name = :instrument_name
            """)
            conn.execute(update_query, {
                "black_scholes_price": row["black_scholes_price"],
                "instrument_name": row["instrument_name"]
            })
    trans.commit()  # Commit changes

print("✅ Black-Scholes prices updated in the database.")
print(df[["instrument_name", "strike_price", "option_type", "black_scholes_price"]].head())
print("ℹ️ Detailed logs are saved in 'black_scholes_log.txt'.")
