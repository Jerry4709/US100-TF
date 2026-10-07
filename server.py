# MT5 -> WebSocket bridge + serves index.html.  Run: python server.py  (opens http://localhost:8765)
# Read-only: only reads prices from MT5, never sends orders.
import asyncio, json, os, time, webbrowser
from pathlib import Path
import numpy as np
import MetaTrader5 as mt5
from websockets.asyncio.server import serve, broadcast

SYMBOLS = ["NAS100Roll.PRO", "US30Roll.PRO"]  # names as shown in MT5 Market Watch
SERVER_UTC_OFFSET_H = 0    # broker server time vs UTC (ACCM = 0, many brokers use 2 or 3)
PORT = 8765
OFFSET_MS = SERVER_UTC_OFFSET_H * 3600_000
RATES_TF = {60_000: mt5.TIMEFRAME_M1, 180_000: mt5.TIMEFRAME_M3, 300_000: mt5.TIMEFRAME_M5,
            900_000: mt5.TIMEFRAME_M15, 1_800_000: mt5.TIMEFRAME_M30,
            3_600_000: mt5.TIMEFRAME_H1, 14_400_000: mt5.TIMEFRAME_H4, 86_400_000: mt5.TIMEFRAME_D1}

if not mt5.initialize():
    raise SystemExit(f"Cannot connect to MT5: {mt5.last_error()} - open MT5 and log in first")
for s in SYMBOLS:
    if not mt5.symbol_select(s, True):
        raise SystemExit(f"Symbol {s} not found in MT5")

def server_now():
    return int(time.time()) + SERVER_UTC_OFFSET_H * 3600

def bars(sym, ms, to, n):
    """n bars ending before `to` (UTC ms, exclusive), or ending now if to is None.
    Rows: [utc_ms, open, high, low, close, tick_volume]. Also returns the newest tick time included."""
    tick = mt5.symbol_info_tick(sym)
    end = server_now() + 1 if to is None else (to + OFFSET_MS) // 1000      # server-time sec, exclusive
    mark = tick.time_msc if tick and tick.time_msc else end * 1000          # server-time ms
    if ms in RATES_TF:
        r = mt5.copy_rates_from(sym, RATES_TF[ms], end - 1, n)
        if r is None or not len(r):
            return [], mark - OFFSET_MS
        rows = np.column_stack([r["time"] * 1000 - OFFSET_MS, r["open"], r["high"], r["low"], r["close"], r["tick_volume"]])
        return rows.tolist(), mark - OFFSET_MS

    # seconds TF: build from ticks. Jump over market-closed gaps using the last M1 bar before `end`.
    last_m1 = mt5.copy_rates_from(sym, mt5.TIMEFRAME_M1, end - 1, 1)
    if last_m1 is None or not len(last_m1):
        return [], mark - OFFSET_MS
    end = min(end, int(last_m1["time"][0]) + 60)
    start = end - n * ms // 1000
    start -= start % (ms // 1000)
    t = mt5.copy_ticks_range(sym, start, end, mt5.COPY_TICKS_ALL)
    if t is None or not len(t):
        return [], mark - OFFSET_MS
    keep = (t["time_msc"] < end * 1000) & (t["time_msc"] <= mark)
    tm, p = t["time_msc"][keep], t["bid"][keep]
    if not len(tm):
        return [], mark - OFFSET_MS
    b = tm - tm % ms                                     # bucket in server time
    idx = np.flatnonzero(np.r_[True, b[1:] != b[:-1]])
    nxt = np.r_[idx[1:], len(p)]
    rows = np.column_stack([b[idx] - OFFSET_MS, p[idx], np.maximum.reduceat(p, idx),
                            np.minimum.reduceat(p, idx), p[nxt - 1], nxt - idx])
    return rows.tolist(), mark - OFFSET_MS

def ticks_since(sym, since_sec, count):
    t = mt5.copy_ticks_from(sym, since_sec, count, mt5.COPY_TICKS_ALL)
    if t is None or len(t) == 0:
        return []
    return [[int(m) - OFFSET_MS, float(b)] for m, b in zip(t["time_msc"], t["bid"])]  # UTC ms, bid

clients = set()
last_msc = {s: server_now() * 1000 - OFFSET_MS for s in SYMBOLS}

# Chart drawings, per symbol: {symbol: [overlay, ...]}
DRAW_FILE = Path(__file__).parent / "drawings.json"
drawings = json.loads(DRAW_FILE.read_text(encoding="utf-8")) if DRAW_FILE.exists() else {}

def save_drawings():
    tmp = DRAW_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(drawings, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, DRAW_FILE)  # atomic: a crash mid-write never corrupts the saved drawings

async def handler(ws):
    await ws.send(json.dumps({"hello": True, "offset": OFFSET_MS, "drawings": drawings,
                              "digits": {s: mt5.symbol_info(s).digits for s in SYMBOLS}}))
    clients.add(ws)
    try:
        # ponytail: MT5 calls block the event loop (~0.5-2s on big tick windows); move to a worker thread if it stutters
        async for msg in ws:
            q = json.loads(msg)
            if q.get("s") not in SYMBOLS:
                continue
            if q.get("op") == "save":
                if isinstance(q.get("overlays"), list):
                    drawings[q["s"]] = q["overlays"]
                    save_drawings()
                continue
            rows, mark = bars(q["s"], int(q["ms"]), q.get("to"), min(int(q.get("n", 1000)), 5000))
            await ws.send(json.dumps({"id": q["id"], "bars": rows, "mark": mark}))
    finally:
        clients.discard(ws)

async def pump():
    # ponytail: polls MT5 every 100ms, fine for a few symbols; use an MQL5 EA push if latency matters
    while True:
        for s in SYMBOLS:
            new = [t for t in ticks_since(s, (last_msc[s] + OFFSET_MS) // 1000, 5000) if t[0] > last_msc[s]]
            if new:
                last_msc[s] = new[-1][0]
                broadcast(clients, json.dumps({"s": s, "ticks": new}))
        await asyncio.sleep(0.1)

def http(conn, req):
    if req.headers.get("Upgrade", "").lower() != "websocket":
        r = conn.respond(200, (Path(__file__).parent / "index.html").read_text(encoding="utf-8"))
        del r.headers["Content-Type"]
        r.headers["Content-Type"] = "text/html; charset=utf-8"
        return r

async def main():
    async with serve(handler, "localhost", PORT, process_request=http):
        print(f"open http://localhost:{PORT}  (Ctrl+C to stop)")
        webbrowser.open(f"http://localhost:{PORT}")
        await pump()

if __name__ == "__main__":
    asyncio.run(main())
