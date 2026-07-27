"""Serves the built dashboard and reruns the conviction pipeline daily.

GitHub Actions' daily cron is disabled for this repo (see
.github/workflows/daily_pipeline.yml) because Yahoo Finance blocks GitHub
Actions' IP ranges. Railway's IPs aren't blocked (verified against the
xin_stock_dashboard project, which hits the same yfinance API from Railway
successfully), so this runs the same five-step pipeline from a persistent
service instead: once at startup, then once per new calendar day.

Writes report JSON straight into dist/reports/ (the directory actually being
served) rather than public/reports/ (Vite's source folder, which only gets
copied into dist/ at build time) so a fresh report is visible immediately
without rebuilding the frontend.
"""

import functools
import http.server
import os
import socketserver
import subprocess
import sys
import threading
import time
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).parent
DIST_DIR = BASE_DIR / "dist"
REPORTS_DIR = DIST_DIR / "reports"

# (script, seconds to sleep after it finishes) — mirrors the rate-limit
# buffers in .github/workflows/daily_pipeline.yml.
STEPS = [
    ("liquidity-regime/scripts/liquidity_regime.py", 45),
    ("forward-earnings/scripts/forward_earnings.py", 45),
    ("market-breadth/scripts/market_breadth.py", 45),
    ("price-signal/scripts/price_signal.py", 15),
]


def run_pipeline() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for script, wait_after in STEPS:
        subprocess.run(
            [sys.executable, str(BASE_DIR / script), "--output-dir", str(REPORTS_DIR)],
            check=True,
            cwd=str(BASE_DIR),
        )
        time.sleep(wait_after)
    subprocess.run(
        [
            sys.executable,
            str(BASE_DIR / "conviction-synthesizer/scripts/conviction_synthesizer.py"),
            "--reports-dir",
            str(REPORTS_DIR),
            "--output-dir",
            str(REPORTS_DIR),
        ],
        check=True,
        cwd=str(BASE_DIR),
    )
    print(f"Pipeline finished for {date.today().isoformat()}", flush=True)


def scheduler_loop() -> None:
    last_run_date = None
    while True:
        today = date.today().isoformat()
        if today != last_run_date:
            try:
                run_pipeline()
                last_run_date = today
            except Exception as exc:  # noqa: BLE001 - keep the loop alive
                print(f"pipeline failed: {exc}", flush=True)
        time.sleep(3600)


if __name__ == "__main__":
    threading.Thread(target=scheduler_loop, daemon=True).start()

    port = int(os.environ.get("PORT", 8000))
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(DIST_DIR)
    )
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving {DIST_DIR} on port {port}", flush=True)
        httpd.serve_forever()
