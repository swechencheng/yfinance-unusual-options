from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
import pandas as pd
import glob
import os

app = FastAPI()

# Mount the static directory
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_root():
    return FileResponse("static/index.html")


@app.get("/api/options/files")
def get_available_files():
    csv_files = glob.glob("unusual_options_us_*.csv")
    if not csv_files:
        csv_files = glob.glob("unusual_options_20*.csv")

    # Sort files by name in descending order (which corresponds to date)
    files = sorted(csv_files, reverse=True)
    return {"files": files}


@app.get("/api/options")
def get_options_data(filename: Optional[str] = None):
    # Only allow fetching CSV files from the current directory to prevent directory traversal
    if (
        filename
        and os.path.exists(filename)
        and filename.endswith(".csv")
        and "/" not in filename
        and "\\" not in filename
    ):
        target_file = filename
    else:
        # Find the most recent US unusual options CSV file
        csv_files = glob.glob("unusual_options_us_*.csv")

        # Fallback to the old naming scheme if we just generated it
        if not csv_files:
            csv_files = glob.glob("unusual_options_20*.csv")

        if not csv_files:
            return {"data": []}

        target_file = max(csv_files, key=os.path.getctime)

    try:
        df = pd.read_csv(target_file)
        # Handle NaN values to ensure valid JSON
        df = df.fillna("")

        # Sort by Estimated_Premium in descending order as default
        if "Estimated_Premium" in df.columns:
            # We must convert to float or int for proper sorting as there might be strings from fillna
            df["Estimated_Premium"] = pd.to_numeric(
                df["Estimated_Premium"], errors="coerce"
            ).fillna(0)
            df = df.sort_values(by="Estimated_Premium", ascending=False)
        elif "Updated" in df.columns:
            df = df.sort_values(by="Updated", ascending=False)

        data = df.to_dict(orient="records")
        return {"data": data, "date": target_file}
    except Exception as e:
        return {"error": str(e), "data": []}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=6003)
