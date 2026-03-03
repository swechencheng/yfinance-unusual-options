import pandas as pd


def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url, storage_options={"User-Agent": "Mozilla/5.0"})
    df = tables[0]
    # Replace dots with hyphens for yfinance compatibility (e.g. BRK.B -> BRK-B)
    tickers = set(df["Symbol"].str.replace(".", "-", regex=False).tolist())
    return tickers


def get_ndx100_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    tables = pd.read_html(url, storage_options={"User-Agent": "Mozilla/5.0"})
    df = None

    # Iterate through tables to find the one with the 'Ticker' column
    for table in tables:
        # Wikipedia changes column names sometimes, handle "Ticker" or "Symbol"
        if "Ticker" in table.columns:
            df = table
            ticker_col = "Ticker"
            break
        elif "Symbol" in table.columns:
            df = table
            ticker_col = "Symbol"
            break

    if df is None:
        raise ValueError("Could not find Nasdaq-100 tickers table on Wikipedia")

    tickers = set(df[ticker_col].str.replace(".", "-", regex=False).tolist())
    return tickers


def main():
    print("Fetching S&P 500 tickers...")
    sp500 = get_sp500_tickers()
    print(f"S&P 500 count: {len(sp500)}")

    print("Fetching Nasdaq-100 tickers...")
    ndx100 = get_ndx100_tickers()
    print(f"Nasdaq-100 count: {len(ndx100)}")

    # Calculate intersection
    intersection = sorted(list(sp500.intersection(ndx100)))
    print(f"\nIntersection count: {len(intersection)}")
    print(f"Intersection tickers: {intersection}")

    with open("tickers_us.txt", "w") as f:
        for ticker in intersection:
            f.write(f"{ticker}\n")
    print("\nSaved intersection tickers to tickers_us.txt")


if __name__ == "__main__":
    main()
