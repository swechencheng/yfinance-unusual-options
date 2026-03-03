import pandas as pd


def get_omxs30_tickers():
    url = "https://en.wikipedia.org/wiki/OMX_Stockholm_30"
    tables = pd.read_html(url, storage_options={"User-Agent": "Mozilla/5.0"})

    # The constituent table is index 1
    df = tables[1]

    if "Ticker" in df.columns:
        tickers = df["Ticker"].tolist()
    else:
        raise ValueError("Could not find Ticker column in OMXS30 table.")

    return tickers


def main():
    print("Fetching OMXS30 tickers...")
    omxs30 = get_omxs30_tickers()
    print(f"OMXS30 count: {len(omxs30)}")

    with open("tickers_omxs30.txt", "w") as f:
        for ticker in sorted(omxs30):
            f.write(f"{ticker}\n")
    print("\nSaved OMXS30 tickers to tickers_omxs30.txt")


if __name__ == "__main__":
    main()
