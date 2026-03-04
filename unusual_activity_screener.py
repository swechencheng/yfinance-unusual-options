import yfinance as yf
import pandas as pd
import datetime
import time
import os
import glob
from apscheduler.schedulers.blocking import BlockingScheduler


def get_unusual_options(tickers_file, vol_oi_ratio_threshold=1.5, min_volume=500):
    try:
        with open(tickers_file, "r") as f:
            tickers = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading tickers file {tickers_file}: {e}")
        return pd.DataFrame()

    all_unusual_options = []

    print(f"Scanning {len(tickers)} tickers for unusual options activity...")

    for i, ticker_symbol in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] Processing {ticker_symbol}...")
        try:
            ticker = yf.Ticker(ticker_symbol)
            expirations = ticker.options

            if not expirations:
                print(f"  No options found for {ticker_symbol}")
                continue

            # Fetch stock price from ~15 mins ago
            stock_price = None
            try:
                hist = ticker.history(period="5d", interval="1m")
                if not hist.empty:
                    target_time = pd.Timestamp.now(tz=hist.index.tz) - pd.Timedelta(
                        minutes=15
                    )
                    past_hist = hist[hist.index <= target_time]
                    if not past_hist.empty:
                        stock_price = float(past_hist["Close"].iloc[-1])
                    else:
                        stock_price = float(hist["Close"].iloc[-1])
            except Exception as e:
                pass

            # Scan the nearest 5 expirations broadly to capture the most active short-term flow.
            # (Scanning all expirations for all tickers can take a very long time and hit rate limits)
            for exp in expirations[:5]:
                try:
                    opt = ticker.option_chain(exp)

                    for option_type, df in [("Call", opt.calls), ("Put", opt.puts)]:
                        if df.empty:
                            continue

                        # Calculate vol/OI ratio, fill 0 or NaN appropriately
                        df = df.copy()
                        # Avoid division by zero by replacing 0 with NaN or 1
                        # If OI is 0 and volume is > 0, that's highly unusual (brand new strike or freshly opened)
                        # We will set openInterest to 1 for division where it is 0, to still get a ratio.
                        df["calc_oi"] = df["openInterest"].replace(0, 1)
                        df["vol/OI"] = df["volume"] / df["calc_oi"]

                        # Ignore corrupted off-hours yfinance data where bid or ask artificially drops to exactly 0.0
                        valid_data_mask = ~((df["bid"] == 0.0) | (df["ask"] == 0.0))

                        mask = (
                            (df["vol/OI"] >= vol_oi_ratio_threshold)
                            & (df["volume"] >= min_volume)
                            & valid_data_mask
                        )
                        unusual = df[mask].copy()

                        if not unusual.empty:
                            unusual["Ticker"] = ticker_symbol
                            unusual["Expiration"] = exp
                            unusual["Type"] = option_type

                            # Estimate Buy/Sell Side based on last price relative to bid/ask
                            # Since yfinance provides aggregated snapshot data, we use a heuristic:
                            # If lastPrice is closer to the ask, it's likely a Buy.
                            # If lastPrice is closer to the bid, it's likely a Sell.
                            def estimate_side(row):
                                try:
                                    bid = float(row["bid"])
                                    ask = float(row["ask"])
                                    last = float(row["lastPrice"])

                                    if (
                                        pd.isna(bid)
                                        or pd.isna(ask)
                                        or (bid == 0 and ask == 0)
                                    ):
                                        return "Unknown"

                                    midpoint = (bid + ask) / 2
                                    if last > midpoint:
                                        return "Buy"
                                    elif last < midpoint:
                                        return "Sell"
                                    else:
                                        return "Neutral"
                                except:
                                    return "Unknown"

                            unusual["Estimated_Side"] = unusual.apply(
                                estimate_side, axis=1
                            )

                            # Estimate total premium exchanged (Volume * Option Price * 100 shares per contract)
                            unusual["Estimated_Premium"] = (
                                (unusual["volume"] * unusual["lastPrice"] * 100)
                                .round()
                                .astype(int)
                            )

                            if stock_price:
                                unusual["Stock_Price"] = round(stock_price, 2)

                                def calc_moneyness(row):
                                    if row["strike"] == 0:
                                        return 0.0
                                    if row["Type"] == "Call":
                                        return (
                                            (stock_price - row["strike"])
                                            / row["strike"]
                                            * 100
                                        )
                                    else:
                                        return (
                                            (row["strike"] - stock_price)
                                            / stock_price
                                            * 100
                                        )

                                unusual["Moneyness"] = unusual.apply(
                                    calc_moneyness, axis=1
                                ).round(2)
                            else:
                                unusual["Stock_Price"] = 0.0
                                unusual["Moneyness"] = 0.0

                            # Select relevant columns and reorder
                            unusual = unusual[
                                [
                                    "Ticker",
                                    "Expiration",
                                    "Type",
                                    "strike",
                                    "Stock_Price",
                                    "lastPrice",
                                    "bid",
                                    "ask",
                                    "volume",
                                    "openInterest",
                                    "vol/OI",
                                    "Moneyness",
                                    "impliedVolatility",
                                    "Estimated_Side",
                                    "Estimated_Premium",
                                ]
                            ]
                            all_unusual_options.append(unusual)

                except Exception as e:
                    pass

        except Exception as e:
            print(f"  Error processing {ticker_symbol}: {e}")

        # Small delay to respect Yahoo Finance rate limits
        time.sleep(0.5)

    if all_unusual_options:
        result_df = pd.concat(all_unusual_options, ignore_index=True)
        return result_df
    else:
        return pd.DataFrame()


def merge_options_data(df_existing, df_new, now_str):
    if "Updated" not in df_existing.columns:
        df_existing["Updated"] = now_str

    df_new = df_new.copy()
    df_new["Updated"] = now_str

    records_existing = df_existing.to_dict("records")
    records_new = df_new.to_dict("records")

    existing_map = {}
    for r in records_existing:
        k = (r["Ticker"], r["Expiration"], r["Type"], r["strike"])
        existing_map[k] = r

    for r in records_new:
        k = (r["Ticker"], r["Expiration"], r["Type"], r["strike"])
        if k in existing_map:
            # Prevent zeroing out valid data from off-market resets
            if r.get("bid") == 0.0 and r.get("ask") == 0.0:
                r["bid"] = existing_map[k].get("bid", 0.0)
                r["ask"] = existing_map[k].get("ask", 0.0)
            if r.get("openInterest") == 0.0:
                r["openInterest"] = existing_map[k].get("openInterest", 0.0)

            changed = False
            check_cols = ["lastPrice", "volume", "openInterest"]
            for col in check_cols:
                old_val = existing_map[k].get(col)
                new_val = r.get(col)

                if pd.isna(old_val) and pd.isna(new_val):
                    continue
                if pd.isna(old_val) != pd.isna(new_val):
                    changed = True
                    break

                if isinstance(old_val, float) and isinstance(new_val, float):
                    if abs(old_val - new_val) > 1e-5:
                        changed = True
                        break
                elif old_val != new_val:
                    changed = True
                    break

            if changed:
                existing_map[k] = r
        else:
            existing_map[k] = r

    result = pd.DataFrame(list(existing_map.values()))
    return result


def filter_previous_day_data(df_new, now_date):
    if df_new.empty:
        return df_new

    csv_files = glob.glob("unusual_options_us_*.csv")
    csv_files = [f for f in csv_files if now_date not in f]

    if not csv_files:
        return df_new

    # Filter data from previous days
    try:
        prev_map = {}
        for prev_file in csv_files:
            try:
                df_prev = pd.read_csv(prev_file)
                for r in df_prev.to_dict("records"):
                    k = (r["Ticker"], r["Expiration"], r["Type"], r["strike"])
                    prev_map[k] = r
            except Exception as e:
                print(f"Error reading previous day data {prev_file}: {e}")

        filtered_records = []
        for r in df_new.to_dict("records"):
            k = (r["Ticker"], r["Expiration"], r["Type"], r["strike"])
            if k in prev_map:
                prev_vals = prev_map[k]

                # If volume is identical to existing data, this is stale pre-market data.
                if r.get("volume") == prev_vals.get("volume"):
                    continue

                # Fix openInterest dropping to 0.0 artificially overnight
                if r.get("openInterest") == 0.0:
                    r["openInterest"] = prev_vals.get("openInterest", 0.0)
                if r.get("bid") == 0.0 and r.get("ask") == 0.0:
                    r["bid"] = prev_vals.get("bid", 0.0)
                    r["ask"] = prev_vals.get("ask", 0.0)

                changed = False
                for col in ["lastPrice", "volume", "openInterest"]:
                    old_val = prev_vals.get(col)
                    new_val = r.get(col)

                    if pd.isna(old_val) and pd.isna(new_val):
                        continue
                    if pd.isna(old_val) != pd.isna(new_val):
                        changed = True
                        break

                    if isinstance(old_val, float) and isinstance(new_val, float):
                        if abs(old_val - new_val) > 1e-5:
                            changed = True
                            break
                    elif old_val != new_val:
                        changed = True
                        break

                if not changed:
                    continue
            filtered_records.append(r)

        return (
            pd.DataFrame(filtered_records)
            if filtered_records
            else pd.DataFrame(columns=df_new.columns)
        )
    except Exception as e:
        print(f"Error processing previous days data: {e}")
        return df_new


def run_screener_job():
    us_tickers_path = "tickers_us.txt"
    if not os.path.exists(us_tickers_path):
        print(f"{us_tickers_path} not found.")
        return

    now_time = datetime.datetime.now()
    now_str = now_time.strftime("%Y-%m-%d %H:%M:%S")
    now_date = now_time.strftime("%Y-%m-%d")

    print(f"\n[{now_str}] Running unusual options scan...")

    df_new = get_unusual_options(
        us_tickers_path,
        vol_oi_ratio_threshold=1.5,
        min_volume=500,
    )

    # Filter out entries that haven't changed since the previous day
    df_new = filter_previous_day_data(df_new, now_date)

    if not df_new.empty:
        output_csv = f"unusual_options_us_{now_date}.csv"

        if os.path.exists(output_csv):
            df_existing = pd.read_csv(output_csv)
            result_df = merge_options_data(df_existing, df_new, now_str)
        else:
            df_new["Updated"] = now_str
            result_df = df_new

        result_df = result_df.sort_values(
            by=["Updated", "Estimated_Premium"], ascending=[False, False]
        )
        result_df.to_csv(output_csv, index=False)
        print(
            f"[{now_str}] Saved/Updated {len(result_df)} unusual options to {output_csv}"
        )
    else:
        print(f"[{now_str}] No unusual options found.")

    print(f"[{now_str}] Scan complete. Waiting for next scheduled run...")


def run_daemon():
    print("Starting Unusual Options Screener Daemon with Cron Timer...")
    # Run once at startup
    run_screener_job()

    # Schedule to run at minutes 0, 15, 30, and 45 of every hour
    scheduler = BlockingScheduler()
    scheduler.add_job(run_screener_job, "cron", minute="0,15,30,45")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Daemon stopped.")


if __name__ == "__main__":
    run_daemon()
