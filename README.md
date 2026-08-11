# NSE Quant Bot

> A Python-based quantitative options analytics toolkit for **NIFTY** that combines live NSE option-chain data, Black–Scholes valuation, Gamma Exposure (GEX) analysis, options strategy construction, and a Streamlit dashboard.

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![NSE](https://img.shields.io/badge/Data-NSE%20India-0B5CAD)](https://www.nseindia.com/)
[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)

## Overview

**NSE Quant Bot** is an experimental quantitative-trading and options-analysis project designed to turn NIFTY option-chain data into actionable analytics and candidate strategies.

The project currently focuses on four areas:

- **Market Data** — retrieves the NIFTY option chain directly from NSE's public endpoint.
- **Quantitative Analytics** — calculates theoretical option values and Gamma using Black–Scholes-based models.
- **Strategy Discovery** — identifies candidate Iron Condors and high-risk/high-reward OTM call opportunities.
- **Market Structure** — estimates Gamma Exposure and highlights strikes with concentrated gamma exposure, referred to by the project as potential gamma walls.

A lightweight **Streamlit dashboard** provides a visual interface for inspecting the option-chain snapshot, candidate calls, GEX levels, and gamma-wall levels.

> **Important:** This is a research and educational project, not a financial-advice or guaranteed-profit system. Options trading involves substantial risk, and model outputs should be independently validated before being used for any live trading decision.

---

## Key Features

### 1. NSE Option-Chain Ingestion

The data layer uses a persistent `requests.Session` to establish a session with NSE and then retrieves the NIFTY option chain.

The normalized dataset contains:

| Field | Description |
|---|---|
| `type` | `call` or `put` |
| `strike` | Option strike price |
| `price` | Latest option price returned by NSE |
| `iv` | Implied volatility |
| `oi` | Open interest |

Implementation: `data_fetcher.py`

### 2. Black–Scholes Analytics

The project implements Black–Scholes calculations for European-style call and put options and exposes a Gamma calculation used by the GEX engine.

The implementation uses:

- Spot price
- Strike price
- Time to expiry
- Risk-free rate
- Implied volatility
- Normal distribution functions from SciPy

Implementation: `black_scholes.py`

### 3. Gamma Exposure (GEX)

The GEX engine calculates an exposure value for each option using estimated Gamma, open interest, and a contract multiplier, then aggregates exposure by strike.

The resulting strike-level data is used to identify the top five gamma-exposure levels.

Implementation: `gex_engine.py`

Conceptually:

```text
Option Chain
     |
     v
Implied Volatility + OI + Strike
     |
     v
Black–Scholes Gamma
     |
     v
Gamma × Open Interest × Contract Multiplier
     |
     v
Aggregate by Strike
     |
     v
Potential Gamma Walls
```

> The current GEX implementation is a simplified research model. It should not be interpreted as a full dealer-positioning model because real-world dealer gamma exposure depends on additional factors such as option direction, contract specifications, expiry structure, hedging assumptions, and position inventory.

### 4. Iron Condor Builder

`iron_condor.py` builds a basic four-leg Iron Condor around the configured spot price.

The current implementation:

1. Separates calls and puts.
2. Finds the call strike closest to spot.
3. Finds the put strike closest to spot.
4. Uses the configured strike distance to construct the long wings.

Example structure:

```text
Long Put  |  Short Put  |  Short Call  |  Long Call
    |             |              |             |
  -200          Spot           Spot          +200
```

The current strategy builder is intentionally simple and should be extended with liquidity, premium, risk/reward, expiry, and breakeven filters before being considered production-ready.

### 5. OTM "Lottery Call" Scanner

The lottery-call scanner searches for call options that satisfy two configurable conditions:

- Strike is more than `LOTTERY_DISTANCE` points above spot.
- Premium is below `LOTTERY_PREMIUM_MAX`.

This is intended as a high-risk/high-upside research screen rather than a recommendation engine.

Implementation: `lottery_calls.py`

### 6. Streamlit Dashboard

The dashboard exposes the main analytics in a simple browser UI:

- Option-chain snapshot
- High-risk OTM calls
- Gamma exposure levels
- Top gamma-wall levels

Run it with:

```bash
streamlit run dashboard.py
```

Implementation: `dashboard.py`

---

## Architecture

```text
                         +----------------------+
                         |      NSE India       |
                         |   NIFTY Option Chain  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   data_fetcher.py    |
                         |  Requests + Pandas   |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   Normalized Data    |
                         | Call / Put / IV / OI |
                         +----------+-----------+
                                    |
                 +------------------+------------------+
                 |                  |                  |
                 v                  v                  v
       +----------------+ +----------------+ +----------------+
       | Black-Scholes  | | Iron Condor    | | Lottery Calls  |
       | + Gamma        | | Strategy       | | Scanner        |
       +-------+--------+ +----------------+ +----------------+
               |
               v
       +----------------+
       |   GEX Engine   |
       | Gamma Exposure |
       +-------+--------+
               |
               v
       +----------------+
       | Gamma Walls    |
       +-------+--------+
               |
        +------+------+
        |             |
        v             v
+---------------+ +---------------+
|   main.py     | | dashboard.py  |
| CLI analytics | |  Streamlit UI |
+---------------+ +---------------+
```

---

## Repository Structure

```text
Nse-Quant-Bot/
├── black_scholes.py      # Black–Scholes pricing and Gamma calculations
├── config.py             # Strategy and model configuration
├── dashboard.py          # Streamlit dashboard
├── data_fetcher.py       # NSE NIFTY option-chain ingestion
├── gex_engine.py         # Gamma Exposure and gamma-wall calculations
├── iron_condor.py        # Basic Iron Condor construction
├── lottery_calls.py      # OTM low-premium call scanner
├── main.py               # Command-line execution entry point
├── requirements.txt      # Python dependencies
├── LICENSE               # GPL-3.0 license
└── README.md             # Project documentation
```

---

## Configuration

Project parameters are centralized in `config.py`.

Current defaults include:

| Parameter | Default | Purpose |
|---|---:|---|
| `SPOT_PRICE` | `22500` | Spot price used by the strategy/model layer |
| `RISK_FREE_RATE` | `0.065` | Risk-free rate used by Black–Scholes |
| `TIME_TO_EXPIRY` | `5/252` | Model time to expiry in years |
| `MISPRICING_THRESHOLD` | `5` | Configured mispricing threshold |
| `IRON_CONDOR_DISTANCE` | `200` | Distance between short and long condor strikes |
| `LOTTERY_PREMIUM_MAX` | `20` | Maximum premium for lottery-call screening |
| `LOTTERY_DISTANCE` | `500` | Minimum OTM distance for lottery-call screening |

The repository also reads `UPSTOX_ACCESS_TOKEN` from the environment:

```bash
export UPSTOX_ACCESS_TOKEN="your_token_here"
```

On Windows PowerShell:

```powershell
$env:UPSTOX_ACCESS_TOKEN="your_token_here"
```

**Do not commit access tokens, API keys, or other secrets to Git.**

> Note: The current repository includes the Upstox Python dependency and configuration placeholder, but the checked-in execution path does not currently place live Upstox order execution in the main workflow. Treat broker integration as an extension point until it is explicitly implemented and tested.

---

## Requirements

The project currently declares the following dependencies:

- NumPy
- Pandas
- SciPy
- Requests
- Numba
- Streamlit
- Upstox Python SDK

Python 3.x is recommended.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/rvats20/Nse-Quant-Bot.git
cd Nse-Quant-Bot
```

### 2. Create a virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## Usage

### Command-line mode

Run the main analytics pipeline:

```bash
python main.py
```

The script will:

1. Fetch the NIFTY option chain.
2. Build a candidate Iron Condor.
3. Scan for high-risk OTM calls.
4. Calculate Gamma Exposure.
5. Identify the top gamma-wall levels.
6. Print the results to the terminal.

Typical output sections look like:

```text
Building strategies...
Iron Condor: {...}
High Risk Calls: [...]
Gamma Wall Levels
...
```

### Dashboard mode

Launch the Streamlit interface:

```bash
streamlit run dashboard.py
```

Streamlit will provide a local URL, typically similar to:

```text
http://localhost:8501
```

---

## How the Quant Pipeline Works

### Step 1 — Fetch market data

`data_fetcher.py` requests the NIFTY option chain from NSE and converts the response into a Pandas DataFrame.

### Step 2 — Normalize calls and puts

Each available call and put is represented as a row with strike, price, IV, and open interest.

### Step 3 — Generate strategy candidates

The strategy modules inspect the normalized option chain and produce candidate structures based on configurable thresholds.

### Step 4 — Calculate Gamma

For each option, Black–Scholes Gamma is calculated from spot, strike, time to expiry, risk-free rate, and IV.

### Step 5 — Estimate GEX

Gamma is combined with open interest and the configured contract multiplier to estimate strike-level gamma exposure.

### Step 6 — Identify gamma walls

The highest exposure strikes are surfaced as potential gamma concentration levels.

### Step 7 — Visualize

The Streamlit dashboard presents the raw option-chain snapshot and the derived analytics in a browser-based interface.

---

## Important Model Assumptions

This repository is intentionally lightweight and should be treated as a **quant research prototype**, not a production trading system.

Important assumptions and limitations include:

- `SPOT_PRICE` is currently configured statically rather than dynamically derived from the option-chain response.
- `TIME_TO_EXPIRY` is configured statically and should be updated dynamically for production use.
- The Black–Scholes implementation assumes the model inputs are valid and does not perform comprehensive input validation.
- GEX is simplified and does not model dealer long/short positioning explicitly.
- The contract multiplier is hard-coded in the GEX calculation and should be validated against the relevant NSE contract specification.
- The Iron Condor builder currently chooses strikes primarily by distance from spot and does not optimize premium, probability of profit, max loss, or expected value.
- The lottery-call scanner is intentionally simplistic and should not be treated as a predictive signal.
- NSE endpoints can change, throttle requests, or require additional headers/session handling.
- No backtesting framework is currently included.
- No portfolio-level risk engine is currently included.
- Live order execution should not be enabled without additional validation, safeguards, logging, and testing.

---

## Risk Disclaimer

This software is provided for **research, experimentation, and educational purposes only**.

It does not constitute investment advice, financial advice, trading advice, or a recommendation to buy or sell any security or derivative.

Options and derivatives can result in substantial losses, including losses exceeding expectations depending on the strategy and account structure. Quantitative models can be wrong, market data can be delayed or incorrect, and historical or model-derived signals do not guarantee future results.

Before using any strategy with real capital:

1. Validate the market-data pipeline.
2. Validate model assumptions.
3. Backtest the strategy on representative historical data.
4. Paper trade the strategy.
5. Add explicit position-sizing and risk controls.
6. Independently verify every order before enabling live execution.

---

## Roadmap

Potential improvements for future versions:

- [ ] Dynamic NIFTY spot-price retrieval
- [ ] Dynamic expiry and time-to-expiry calculation
- [ ] Automatic expiry discovery from NSE data
- [ ] Better NSE request/session resilience and rate-limit handling
- [ ] Option liquidity and bid/ask spread filters
- [ ] Put/Call OI and volume analytics
- [ ] IV skew and term-structure analysis
- [ ] Volatility surface construction
- [ ] More rigorous dealer GEX modeling
- [ ] Gamma flip / zero-gamma level detection
- [ ] Max pain calculation
- [ ] Strategy P&L and payoff visualization
- [ ] Probability-of-profit calculations
- [ ] Historical backtesting engine
- [ ] Walk-forward testing
- [ ] Portfolio and position-risk management
- [ ] Structured logging and audit trails
- [ ] Automated data caching
- [ ] Unit and integration tests
- [ ] CI/CD with GitHub Actions
- [ ] Paper-trading integration
- [ ] Production-grade broker execution with kill switches and order validation

---

## Development

Recommended workflow for contributors:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
streamlit run dashboard.py
```

Before submitting changes, validate that:

- Existing modules still import successfully.
- NSE data parsing continues to work.
- Strategy outputs are structurally valid.
- Model calculations are numerically stable.
- No credentials or secrets are committed.
- Changes to trading logic are accompanied by tests or reproducible examples.

---

## Contributing

Contributions are welcome.

For substantial changes:

1. Fork the repository.
2. Create a feature branch.
3. Make the change with focused commits.
4. Add tests where practical.
5. Update documentation when behavior changes.
6. Open a pull request describing the change and its validation.

For trading-related functionality, explain the model assumptions and risk implications in the pull request.

---

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for details.

---

## Author

**Rahul Vats**

GitHub: [@rvats20](https://github.com/rvats20)

---

## Project Status

**Status: Experimental / Research Prototype**

The project is suitable for exploring quantitative options analytics and building a foundation for a more robust NIFTY research platform. It is **not currently a production-grade autonomous trading system**.
