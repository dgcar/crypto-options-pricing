"""
Compares Black-Scholes and Heston model option prices against real market prices.

This script retrieves option pricing data from the database, calculates absolute errors for both models,
and generates visualizations to compare their pricing accuracy.

Key Features:
- Fetches option pricing data, including Black-Scholes, Heston, and real market prices.
- Converts real market prices to USD using the latest spot price.
- Computes absolute errors for Black-Scholes and Heston models.
- Generates scatter plots comparing model prices to real market prices.
- Creates bar charts to visualize the mean absolute error of both models.
- Prints summary statistics of the model errors.

This script is part of a broader project that evaluates the accuracy of the Black-Scholes and Heston models for pricing cryptocurrency options.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

# Database connection settings (Replace placeholders with actual credentials)
DB_NAME = "your_database"
DB_USER = "your_username"
DB_PASSWORD = "your_password"
DB_HOST = "your_host"
DB_PORT = "5432"

# Create database connection
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Fetch option pricing data
query = """
    SELECT o.instrument_name, o.strike_price, o.option_type, cr.symbol, 
           p.close AS spot_price, o.heston_price, o.black_scholes_price, d.real_market_price
    FROM crypto_options o
    JOIN crypto_prices p ON o.crypto_id = p.crypto_id
    JOIN cryptocurrencies cr ON p.crypto_id = cr.crypto_id
    LEFT JOIN deribit_options d ON o.instrument_name = d.instrument_name
    WHERE o.heston_price IS NOT NULL AND o.black_scholes_price IS NOT NULL
    ORDER BY p.timestamp DESC
"""
df = pd.read_sql(query, con=engine)

# Ensure data is not empty
if df.empty:
    print("❌ ERROR: No valid data fetched from the database!")
    exit()

# Convert real market prices to USD
print("✅ Converting real market prices to USD...")
df["real_market_price"] = df["real_market_price"] * df["spot_price"]

# Calculate absolute errors
print("✅ Calculating absolute errors...")
df["error_bs"] = np.abs(df["black_scholes_price"] - df["real_market_price"])
df["error_heston"] = np.abs(df["heston_price"] - df["real_market_price"])

# Visualize model comparison
plt.figure(figsize=(10, 5))
plt.scatter(df["real_market_price"], df["black_scholes_price"], color='blue', label='Black-Scholes', alpha=0.5)
plt.scatter(df["real_market_price"], df["heston_price"], color='red', label='Heston', alpha=0.5)
plt.plot([df["real_market_price"].min(), df["real_market_price"].max()],
         [df["real_market_price"].min(), df["real_market_price"].max()], 'k--', label='Perfect Fit')
plt.xlabel("Real Market Price (USD)")
plt.ylabel("Model Price (USD)")
plt.title("Black-Scholes vs Heston Model vs Market Prices")
plt.legend()
plt.grid(True)
plt.show()

# Compare absolute errors
plt.figure(figsize=(10, 5))
plt.bar(["Black-Scholes", "Heston"], [df["error_bs"].mean(), df["error_heston"].mean()], color=['blue', 'red'])
plt.ylabel("Mean Absolute Error (USD)")
plt.title("Average Absolute Errors of Models")
plt.grid(axis='y')
plt.show()

# Print summary statistics
print("📊 Model Error Summary:")
print(df[["error_bs", "error_heston"]].describe())
