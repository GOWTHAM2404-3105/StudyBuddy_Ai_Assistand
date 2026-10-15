"""Dataset download and verification script for UCI Student Performance dataset."""

import os
import urllib.request
import zipfile
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
UCI_URL = "https://archive.ics.uci.edu/static/public/320/student+performance.zip"


def download_and_extract():
    """Download and extract the UCI Student Performance dataset."""
    target_csv = DATA_DIR / "student-mat.csv"
    if target_csv.exists():
        print(f"[OK] Dataset already exists at: {target_csv}")
        return True

    print(f"Downloading UCI Student Performance dataset from {UCI_URL}...")
    zip_path = DATA_DIR / "temp_uci.zip"

    try:
        urllib.request.urlretrieve(UCI_URL, zip_path)
        print("Extracting outer zip...")
        with zipfile.ZipFile(zip_path, "r") as outer:
            outer.extractall(DATA_DIR)

        inner_zip = DATA_DIR / "student.zip"
        if inner_zip.exists():
            print("Extracting inner student.zip...")
            with zipfile.ZipFile(inner_zip, "r") as inner:
                inner.extractall(DATA_DIR)
            inner_zip.unlink()

        # Clean up temporary zip
        if zip_path.exists():
            zip_path.unlink()

        old_zip = DATA_DIR / ".student.zip_old"
        if old_zip.exists():
            old_zip.unlink()

        print(f"[OK] Successfully extracted dataset to: {DATA_DIR}")
        return True
    except Exception as e:
        print(f"Error downloading dataset: {e}")
        return False


if __name__ == "__main__":
    download_and_extract()
