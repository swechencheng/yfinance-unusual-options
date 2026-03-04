# yfinance-unusual-options

A tool for tracking and visualizing unusual options activity for US equities using `yfinance`.

This project consists of a background screener daemon that periodically scans for unusual options activities and a FastAPI web backend that serves the data to a responsive frontend grid.

## Features

- **Automated Screener**: A scheduled background job (powered by `apscheduler`) that scans a custom list of US tickers (`tickers_us.txt`) every 15 minutes.
- **Unusual Detection Criteria**: Flags options where Volume/Open Interest ratio is $\ge$ 1.5 and Volume is $\ge$ 500.
- **Side Estimation**: Infers whether trades were likely bought or sold based on the last transaction price relative to the bid/ask spread.
- **Historical Tracking**: Merges new data with previous scans, persisting a daily CSV registry (`unusual_options_us_{date}.csv`). Data updates throughout the day without overwriting old meaningful data (fixes 0.0 off-hours `yfinance` discrepancies).
- **FastAPI Web Interface**: Lightweight API serving the CSV data to a web frontend on port 6003. Let's you view previous history and filter live unusual options in your browser.

## Prerequisites

- Python >= 3.6
- macOS / Linux / Windows

## Installation

1. **Clone the repository:**

```bash
git clone https://github.com/pacavanza/yfinance-unusual-options.git
cd yfinance-unusual-options
```

2. **Set up a Virtual Environment and install dependencies:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

3. **Provide Tickers:**

Make sure `tickers_us.txt` is populated with a newline-separated list of symbols you want to track (e.g. `AAPL`, `TSLA`, `SPY`).

## Usage

### 1. Run the Screener Daemon

The screener runs in a continuous loop, analyzing data on 15-minute intervals.

```bash
python unusual_activity_screener.py
```

_This will generate `unusual_options_us_YYYY-MM-DD.csv` files._

### 2. Run the Web Interface

In a separate terminal, start the FastAPI web server to view the dashboard:

```bash
python backend.py
```

Open a browser and navigate to: [http://localhost:6003](http://localhost:6003)

## Directory Structure

- `unusual_activity_screener.py`: Daemon script for fetching, filtering and storing unusual options data.
- `backend.py`: FastAPI backend that exposes the `/api/options` endpoints.
- `static/`: HTML/JS/CSS files for the Web Dashboard.
- `tickers_us.txt`: Customizable list of ticker symbols to be scanned.
- `requirements.txt`: Python package requirements.

## License

MIT
