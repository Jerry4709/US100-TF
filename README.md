# Scalp Chart — US100 / US30

Realtime chart from 5-second bars up to daily. Read-only: never sends orders.

**Online:** https://jerry4709.github.io/US100-TF/ — open in any browser, no install, no MT5.

- KLineChart Pro UI: drawing tools, indicators, 5s · 10s · 15s · 30s · 1m · 3m · 5m · 15m · 30m · 1H · 4H · D
- Side-by-side US100 / US30 compare
- ICT Sessions & Killzones in New York time, DST-aware (edit `KZ` in `index.html`), killzone highs/lows extend until taken
- Right-click menu, Alt+R resets the chart view
- Drawings are remembered per symbol

## Two data sources, same page

| Opened from | Prices | History | Drawings saved to |
|---|---|---|---|
| Anywhere (GitHub Pages) | US100: OKX Nasdaq-100 index. US30: Bitget `DIASTOCKUSDT` index x100 (DIA ETF) | 1m+ back months; US100 second TFs ~3 weeks (scroll left); US30 second TFs only from page open | your browser (localStorage) |
| `start.bat` on a PC with MT5 | your broker's MT5 feed | ~1 month, incl. tick-built second bars | `drawings.json` |

### Local MT5 mode (Windows)

1. Open MT5 and log in. Symbol names and broker UTC offset are at the top of `server.py`.
2. `pip install MetaTrader5 websockets numpy`
3. Double-click `start.bat` (opens http://localhost:8765)
