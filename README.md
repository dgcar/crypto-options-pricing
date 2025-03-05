# 🚀 Cryptocurrency Options Pricing Project

This project analyzes and prices cryptocurrency options using two major financial models:

- **Black-Scholes Model**: Assumes constant volatility and is widely used for pricing options in traditional markets.
- **Heston Stochastic Volatility Model**: Incorporates changing volatility over time, making it more suitable for assets like cryptocurrencies with highly variable volatility.

The project retrieves real-world options data from **Deribit**, calculates theoretical prices using both models, and compares them to actual market prices to evaluate which model provides a better fit for crypto options.

---

## 📂 Project Structure
```
crypto-options-pricing/
│── database/
│   ├── schema.sql          # PostgreSQL database structure
│
│── data/
│   ├── fetch_crypto_options.py  # Fetches options data
│   ├── fetch_crypto_prices.py   # Fetches spot prices
│   ├── fetch_deribit_options.py # Fetches Deribit options
│
│── scripts/
│   ├── black_scholes.py         # Computes Black-Scholes prices
│   ├── heston_model.py          # Computes Heston model prices
│   ├── compare.py               # Compares both models with market prices
│   ├── black_scholes_vis.py     # Visualizes Black-Scholes results
│   ├── heston_vis.py            # Visualizes Heston results
│
│── README.md                    # Project documentation
```

---

## 🚀 Installation & Setup

### 1️⃣ Clone the Repository
```sh
git clone https://github.com/YOUR_USERNAME/crypto-options-pricing.git
cd crypto-options-pricing
```

### 2️⃣ Install Dependencies
```sh
pip install numpy pandas scipy matplotlib sqlalchemy psycopg2 requests numba
```

### 3️⃣ Set Up the Database
Ensure you have **PostgreSQL** installed, then create the database:
```sh
psql -U your_username -d crypto_info -f database/schema.sql
```

---

## 📊 Running the Models

### 1️⃣ Fetch and Store Market Data
```sh
python data/fetch_crypto_options.py
python data/fetch_crypto_prices.py
python data/fetch_deribit_options.py
```

### 2️⃣ Compute Theoretical Prices
#### ➤ Black-Scholes Model:
```sh
python scripts/black_scholes.py
```
#### ➤ Heston Model:
```sh
python scripts/heston_model.py
```

### 3️⃣ Compare and Visualize Results
#### ➤ Compare Both Models:
```sh
python scripts/compare.py
```
#### ➤ Visualize Black-Scholes:
```sh
python scripts/black_scholes_vis.py
```
#### ➤ Visualize Heston:
```sh
python scripts/heston_vis.py
```

---

## 📈 Expected Results
This project evaluates how well **Black-Scholes and Heston models** match real market prices. The comparison includes:
- **Mean Absolute Errors (MAE)**
- **Visualization of pricing differences**
- **Heston parameter calibration results**

