# Scalp Chart — US100 / US30

Realtime chart for second timeframes (5s–30s) up to D, fed by MetaTrader 5. Read-only: never sends orders.

- KLineChart Pro UI: drawing tools, indicators, 5s · 10s · 15s · 30s · 1m · 3m · 5m · 15m · 30m · 1H · 4H · D
- ~1 month history (tick-built second bars, MT5 bars for 1m+), loads more when you scroll left
- Drawings saved per symbol to `drawings.json`
- Side-by-side US100 / US30 compare
- ICT Sessions & Killzones (UTC times, edit `KZ` in `index.html`), killzone highs/lows extend until taken
- Right-click menu, Alt+R resets the chart view

## Run (Windows)

1. Open MT5 and log in. Symbol names and broker UTC offset are at the top of `server.py`.
2. `pip install MetaTrader5 websockets numpy`
3. Double-click `start.bat` (opens http://localhost:8765)
