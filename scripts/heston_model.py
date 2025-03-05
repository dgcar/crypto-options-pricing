"""
Calculates cryptocurrency option prices using the Heston stochastic volatility model.

This script retrieves real market data from the database, calibrates the Heston model parameters,
and computes theoretical option prices based on the Heston model. The results are then stored back in the database.

Key Features:
- Fetches market data including spot prices, strike prices, expiration dates, and implied volatilities.
- Converts expiration timestamps to time-to-expiry (T) in years.
- Implements the Heston characteristic function for option pricing.
- Uses numerical integration (Fourier transform) to compute Heston model prices.
- Calibrates model parameters (kappa, theta, rho, v0) using real market prices.
- Applies corrections for deep out-of-the-money options and removes extreme outliers.
- Updates the PostgreSQL database with Heston model prices.

This script is part of a broader project that compares the Black-Scholes and Heston models for pricing cryptocurrency options.
"""

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from scipy.integrate import quad
from scipy.optimize import minimize
from numba import jit

# Database connection settings (Replace placeholders with actual credentials)
DB_NAME = "your_database"
DB_USER = "your_username"
DB_PASSWORD = "your_password"
DB_HOST = "your_host"
DB_PORT = "5432"

# Create database connection
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Fetch and process option data
query = """
    SELECT o.instrument_name, o.strike_price, o.expiration_date, o.option_type, cr.symbol, 
           p.close AS spot_price, d.real_market_price, d.implied_volatility
    FROM crypto_options o
    JOIN crypto_prices p ON o.crypto_id = p.crypto_id
    JOIN cryptocurrencies cr ON p.crypto_id = cr.crypto_id
    LEFT JOIN deribit_options d ON o.instrument_name = d.instrument_name
    ORDER BY p.timestamp DESC
"""
df = pd.read_sql(query, con=engine)
if df.empty:
    print("❌ ERROR: No data was fetched from the database!")
    exit()

# Convert expiration date and calculate time to expiry in years
df["expiration_date"] = pd.to_datetime(df["expiration_date"], unit="s")
current_time = pd.Timestamp.now()
df["T"] = (df["expiration_date"] - current_time).dt.total_seconds() / (365 * 24 * 60 * 60)
df = df[df["T"] > (14 / 365)]  # Exclude options with less than 14 days to expiration

df = df.dropna(subset=["real_market_price", "implied_volatility"])
df = df[(df['strike_price'] < 2.5 * df['spot_price']) & (df['strike_price'] > 0.4 * df['spot_price'])]  # Reduced to 500 for faster calibration

@jit(nopython=True)
def heston_cf(phi, S, T, r, kappa, theta, sigma, rho, v0, j):
    i = 1j
    u = 0.5 if j == 1 else -0.5
    b = kappa - rho * sigma if j == 1 else kappa

    d = np.sqrt((rho * sigma * i * phi - b)**2 - sigma**2 * (2 * u * i * phi - phi**2))
    g = (b - rho * sigma * i * phi + d) / (b - rho * sigma * i * phi - d)
    C = r * i * phi * T + (kappa * theta / sigma**2) * ((b - rho * sigma * i * phi + d)*T - 2 * np.log((1 - g * np.exp(d * T)) / (1 - g)))
    D = ((b - rho * sigma * i * phi + d) / sigma**2) * ((1 - np.exp(d * T)) / (1 - g * np.exp(d * T)))
    return np.exp(C + D * v0 + i * phi * np.log(S))

@jit(nopython=True)
def integrand(phi, S, K, T, r, kappa, theta, sigma, rho, v0, j):
    i = 1j
    return (np.exp(-i * phi * np.log(K)) * heston_cf(phi, S, T, r, kappa, theta, sigma, rho, v0, j) / (i * phi)).real if phi != 0 else 0.0

def heston_price(S, K, T, r, kappa, theta, sigma, rho, v0, option_type):
    phi_max = 85  # Increased for better precision
    quad_options = {'limit': 300, 'epsabs': 1e-6, 'epsrel': 1e-6}  # Higher precision
    
    P1 = 0.5 + (1/np.pi) * quad(integrand, 0, phi_max, args=(S, K, T, r, kappa, theta, sigma, rho, v0, 1), **quad_options)[0]
    P2 = 0.5 + (1/np.pi) * quad(integrand, 0, phi_max, args=(S, K, T, r, kappa, theta, sigma, rho, v0, 2), **quad_options)[0]
    
    if option_type == "call":
        price = S * P1 - K * np.exp(-r * T) * P2
    elif option_type == "put":
        price = K * np.exp(-r * T) * (1 - P2) - S * (1 - P1)
    else:
        return None
    
    return max(price, 0)

def calibration_objective(params, data, r_fixed):
    kappa, theta, rho, v0 = params
    error = 0.0
    for _, row in data.iterrows():
        S, K, T = row["spot_price"], row["strike_price"], row["T"]
        option_type, market_price, sigma = row["option_type"].lower().strip(), row["real_market_price"], row["implied_volatility"]
        model_price = heston_price(S, K, T, r_fixed, kappa, theta, sigma, rho, v0, option_type)
        if market_price > 0:
            error += ((model_price - market_price) / market_price) ** 2  # Normalize error
    return error

r_fixed = 0.045
bounds = [(1.0, 5), (0.02, 0.2), (-0.9, -0.3), (0.02, 0.3)]  # Tighter bounds for stability
# Use predefined realistic initial parameters for crypto options
initial_guess = [3.0, 0.05, -0.6, 0.1]  # More realistic crypto parameters

# Only use L-BFGS-B for fast calibration
result = minimize(calibration_objective, initial_guess, args=(df, r_fixed), bounds=bounds, method='L-BFGS-B')

if result.success:
    kappa, theta, rho, v0 = result.x
    print(f"✅ Optimized Parameters: kappa={kappa:.4f}, theta={theta:.4f}, rho={rho:.4f}, v0={v0:.4f}")
else:
    print("⚠️ Optimization failed! Using default values.")
    kappa, theta, rho, v0 = [2.0, 0.04, -0.7, 0.04]

df["heston_price"] = df.apply(lambda row: heston_price(row["spot_price"], row["strike_price"], row["T"], r_fixed, kappa, theta, row["implied_volatility"], rho, v0, row["option_type"]) if row["real_market_price"] > 0 else None, axis=1)

# Apply correction for deep out-of-the-money options
df["heston_price"] = np.where(
    df["strike_price"] > df["spot_price"] * 1.5,
    df["heston_price"] * 0.95,  # Small downward adjustment for deep OTM options
    df["heston_price"]
)

# Remove extreme outliers
df["error_heston"] = abs(df["heston_price"] - df["real_market_price"])
df = df[df["error_heston"] < df["error_heston"].quantile(0.975)]

# Remove NaNs before updating database
df = df.dropna(subset=["heston_price"])

# Update database with Heston prices
with engine.connect() as conn:
    trans = conn.begin()
    for _, row in df.iterrows():
        conn.execute(text("""
            UPDATE crypto_options SET heston_price = :heston_price 
            WHERE instrument_name = :instrument_name
        """), {"heston_price": row["heston_price"], "instrument_name": row["instrument_name"]})
    trans.commit()

print("✅ Heston Model prices updated in the database.")
