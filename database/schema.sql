-- PostgreSQL schema for cryptocurrency options pricing project

-- Table: cryptocurrencies
CREATE TABLE public.cryptocurrencies (
    crypto_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL
);

-- Table: crypto_prices
CREATE TABLE public.crypto_prices (
    price_id SERIAL PRIMARY KEY,
    crypto_id INTEGER REFERENCES public.cryptocurrencies(crypto_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    open NUMERIC(18,8) NOT NULL,
    high NUMERIC(18,8) NOT NULL,
    low NUMERIC(18,8) NOT NULL,
    close NUMERIC(18,8) NOT NULL,
    volume NUMERIC(22,8) NOT NULL,
    symbol TEXT,
    CONSTRAINT crypto_prices_crypto_id_timestamp_key UNIQUE (crypto_id, timestamp)
);

-- Indexes for crypto_prices
CREATE INDEX idx_crypto_prices_crypto_id ON public.crypto_prices (crypto_id);
CREATE INDEX idx_crypto_prices_timestamp ON public.crypto_prices (timestamp);

-- Table: crypto_options
CREATE TABLE public.crypto_options (
    instrument_name TEXT,
    expiration_date BIGINT,
    strike_price DOUBLE PRECISION,
    option_type TEXT,
    timestamp TIMESTAMP WITHOUT TIME ZONE,
    crypto_id BIGINT REFERENCES public.cryptocurrencies(crypto_id),
    black_scholes_price NUMERIC(18,8),
    heston_price DOUBLE PRECISION
);

-- Table: deribit_options
CREATE TABLE public.deribit_options (
    option_id SERIAL PRIMARY KEY,
    crypto_id INTEGER REFERENCES public.cryptocurrencies(crypto_id),
    symbol TEXT NOT NULL,
    strike_price NUMERIC(18,8) NOT NULL,
    option_type TEXT NOT NULL CHECK (option_type IN ('call', 'put')),
    expiration_date BIGINT NOT NULL,
    real_market_price NUMERIC(18,8) NOT NULL,
    instrument_name TEXT,
    implied_volatility DOUBLE PRECISION
);

-- Foreign key constraints
ALTER TABLE public.crypto_prices
    ADD CONSTRAINT crypto_prices_crypto_id_fkey FOREIGN KEY (crypto_id) REFERENCES public.cryptocurrencies(crypto_id) ON DELETE CASCADE;

ALTER TABLE public.deribit_options
    ADD CONSTRAINT deribit_options_crypto_id_fkey FOREIGN KEY (crypto_id) REFERENCES public.cryptocurrencies(crypto_id);
