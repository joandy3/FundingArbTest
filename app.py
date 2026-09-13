"""
app.py — Binance Futures: Funding Fee & Order Viewer
-----------------------------------------------------
Single-file Flask app. Run locally:

    pip install flask requests
    python app.py

Then open http://127.0.0.1:5000

You enter YOUR OWN Binance API Key/Secret in the browser form.
Keys are kept only in your local session cookie (not written to disk,
not sent anywhere except signed requests straight to Binance's API).

Security notes (read before using with a real key):
- Create the API key on Binance with READ-ONLY permission
  (do NOT enable withdrawals or trading) if you only want to view data.
- This app is meant for local/personal use. Don't deploy it publicly
  as-is with debug=True or without HTTPS + a real secret key.
"""

import os
import time
import hmac
import hashlib
import secrets
import requests
from flask import Flask, render_template_string, request, session, redirect, url_for

app = Flask(__name__)

# Secret key for signing the session cookie itself (NOT your Binance key).
# Set FLASK_SECRET_KEY in your environment for a stable value across restarts;
# otherwise a random one is generated each run (fine for local single-user use,
# but it means everyone gets logged out whenever you restart the app).
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

# Debug mode is OFF by default. Only enable it locally via:
#   FLASK_DEBUG=1 python app.py
# Never enable it if the app is reachable from outside your machine.
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "0") == "1"

BASE_URL = "https://fapi.binance.com"

# Binance API key/secret are kept server-side in memory only, keyed by a random
# per-login token. The browser session cookie stores just that opaque token —
# never the real key/secret — so inspecting the cookie reveals nothing useful.
# Restarting the app clears this store, which is expected (just log in again).
_CREDENTIAL_STORE = {}


def save_credentials(api_key, api_secret):
    token = secrets.token_urlsafe(32)
    _CREDENTIAL_STORE[token] = {"api_key": api_key, "api_secret": api_secret}
    return token


def get_credentials():
    token = session.get("cred_token")
    if not token:
        return None, None
    creds = _CREDENTIAL_STORE.get(token)
    if not creds:
        return None, None
    return creds["api_key"], creds["api_secret"]


def clear_credentials():
    token = session.pop("cred_token", None)
    if token:
        _CREDENTIAL_STORE.pop(token, None)


# ---------------------------------------------------------------------------
# Binance signed-request helper
# ---------------------------------------------------------------------------
def binance_signed_get(endpoint, api_key, api_secret, params=None):
    """Call a Binance Futures signed GET endpoint and return parsed JSON."""
    params = dict(params or {})
    params["timestamp"] = int(time.time() * 1000)
    params.setdefault("recvWindow", 5000)

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    signature = hmac.new(
        api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": api_key}

    resp = requests.get(url, headers=headers, timeout=10)
    data = resp.json()
    if resp.status_code != 200:
        msg = data.get("msg", str(data)) if isinstance(data, dict) else str(data)
        raise RuntimeError(f"Binance API error ({resp.status_code}): {msg}")
    return data


# ---------------------------------------------------------------------------
# Templates (Tailwind via CDN)
# ---------------------------------------------------------------------------
BASE_HEAD = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<title>Binance Futures Viewer</title>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>""" + BASE_HEAD + """</head>
<body class="bg-gray-950 text-gray-100 min-h-screen flex items-center justify-center">
  <div class="w-full max-w-md bg-gray-900 border border-gray-800 rounded-2xl p-8 shadow-xl">
    <h1 class="text-xl font-semibold mb-1">Binance Futures Viewer</h1>
    <p class="text-gray-400 text-sm mb-6">กรอก API Key / Secret ของคุณ (แนะนำให้สร้างคีย์แบบ Read-Only)</p>

    {% if error %}
    <div class="mb-4 text-sm text-red-300 bg-red-950 border border-red-800 rounded-lg px-3 py-2">
      {{ error }}
    </div>
    {% endif %}

    <form method="POST" class="space-y-4">
      <div>
        <label class="block text-sm text-gray-300 mb-1">API Key</label>
        <input type="text" name="api_key" required
               class="w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm
                      focus:outline-none focus:ring-2 focus:ring-yellow-500">
      </div>
      <div>
        <label class="block text-sm text-gray-300 mb-1">API Secret</label>
        <input type="password" name="api_secret" required
               class="w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm
                      focus:outline-none focus:ring-2 focus:ring-yellow-500">
      </div>
      <button type="submit"
              class="w-full bg-yellow-500 hover:bg-yellow-400 text-gray-950 font-medium
                     rounded-lg py-2 text-sm transition">
        เชื่อมต่อ
      </button>
    </form>

    <p class="text-xs text-gray-500 mt-6 leading-relaxed">
      คีย์จะถูกเก็บเฉพาะใน session cookie ของเบราว์เซอร์นี้ ไม่ถูกบันทึกลงไฟล์ใด ๆ
      และถูกส่งไปยัง Binance API โดยตรงเท่านั้น
    </p>
  </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>""" + BASE_HEAD + """</head>
<body class="bg-gray-950 text-gray-100 min-h-screen">
  <div class="max-w-5xl mx-auto px-4 py-8">

    <div class="flex items-center justify-between mb-8">
      <h1 class="text-xl font-semibold">Binance Futures Dashboard</h1>
      <a href="{{ url_for('logout') }}"
         class="text-sm text-gray-400 hover:text-red-400 transition">ออกจากระบบ</a>
    </div>

    {% if error %}
    <div class="mb-6 text-sm text-red-300 bg-red-950 border border-red-800 rounded-lg px-4 py-3">
      {{ error }}
    </div>
    {% endif %}

    <!-- Funding Fee -->
    <div class="bg-gray-900 border border-gray-800 rounded-2xl p-6 mb-8">
      <h2 class="font-medium mb-4">Funding Fee ล่าสุด</h2>
      {% if funding_fees %}
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-400 border-b border-gray-800">
              <th class="py-2 pr-4">เวลา</th>
              <th class="py-2 pr-4">Symbol</th>
              <th class="py-2 pr-4 text-right">จำนวน (USDT)</th>
            </tr>
          </thead>
          <tbody>
            {% for f in funding_fees %}
            <tr class="border-b border-gray-800/50">
              <td class="py-2 pr-4 text-gray-300">{{ f.time_str }}</td>
              <td class="py-2 pr-4">{{ f.symbol }}</td>
              <td class="py-2 pr-4 text-right {{ 'text-red-400' if f.amount_val < 0 else 'text-green-400' }}">
                {{ f.income }}
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <p class="text-gray-500 text-sm">ไม่พบข้อมูล funding fee ในช่วงที่ดึงมา</p>
      {% endif %}
    </div>

    <!-- Open Orders -->
    <div class="bg-gray-900 border border-gray-800 rounded-2xl p-6 mb-8">
      <h2 class="font-medium mb-4">Open Orders (คำสั่งที่ยังค้างอยู่)</h2>
      {% if open_orders %}
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-400 border-b border-gray-800">
              <th class="py-2 pr-4">Symbol</th>
              <th class="py-2 pr-4">Side</th>
              <th class="py-2 pr-4">Type</th>
              <th class="py-2 pr-4 text-right">Price</th>
              <th class="py-2 pr-4 text-right">Qty</th>
              <th class="py-2 pr-4">Status</th>
            </tr>
          </thead>
          <tbody>
            {% for o in open_orders %}
            <tr class="border-b border-gray-800/50">
              <td class="py-2 pr-4">{{ o.symbol }}</td>
              <td class="py-2 pr-4 {{ 'text-green-400' if o.side == 'BUY' else 'text-red-400' }}">{{ o.side }}</td>
              <td class="py-2 pr-4">{{ o.type }}</td>
              <td class="py-2 pr-4 text-right">{{ o.price }}</td>
              <td class="py-2 pr-4 text-right">{{ o.origQty }}</td>
              <td class="py-2 pr-4 text-gray-400">{{ o.status }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <p class="text-gray-500 text-sm">ไม่มี open orders ในตอนนี้</p>
      {% endif %}
    </div>

    <!-- Order history by symbol -->
    <div class="bg-gray-900 border border-gray-800 rounded-2xl p-6">
      <h2 class="font-medium mb-4">ประวัติคำสั่งซื้อขาย (ระบุ Symbol)</h2>
      <form method="GET" class="flex gap-2 mb-4">
        <input type="text" name="symbol" placeholder="เช่น BTCUSDT"
               value="{{ symbol or '' }}"
               class="flex-1 rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm
                      focus:outline-none focus:ring-2 focus:ring-yellow-500">
        <button type="submit"
                class="bg-yellow-500 hover:bg-yellow-400 text-gray-950 font-medium
                       rounded-lg px-4 py-2 text-sm transition">ค้นหา</button>
      </form>

      {% if symbol and order_history is not none %}
        {% if order_history %}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-gray-400 border-b border-gray-800">
                <th class="py-2 pr-4">เวลา</th>
                <th class="py-2 pr-4">Side</th>
                <th class="py-2 pr-4">Type</th>
                <th class="py-2 pr-4 text-right">Price</th>
                <th class="py-2 pr-4 text-right">Qty</th>
                <th class="py-2 pr-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {% for o in order_history %}
              <tr class="border-b border-gray-800/50">
                <td class="py-2 pr-4 text-gray-300">{{ o.time_str }}</td>
                <td class="py-2 pr-4 {{ 'text-green-400' if o.side == 'BUY' else 'text-red-400' }}">{{ o.side }}</td>
                <td class="py-2 pr-4">{{ o.type }}</td>
                <td class="py-2 pr-4 text-right">{{ o.price }}</td>
                <td class="py-2 pr-4 text-right">{{ o.origQty }}</td>
                <td class="py-2 pr-4 text-gray-400">{{ o.status }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        {% else %}
        <p class="text-gray-500 text-sm">ไม่พบคำสั่งซื้อขายของ {{ symbol }}</p>
        {% endif %}
      {% endif %}
    </div>

  </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        api_key = request.form.get("api_key", "").strip()
        api_secret = request.form.get("api_secret", "").strip()
        if not api_key or not api_secret:
            return render_template_string(LOGIN_TEMPLATE, error="กรุณากรอก API Key และ API Secret ให้ครบ")
        session["cred_token"] = save_credentials(api_key, api_secret)
        return redirect(url_for("dashboard"))
    return render_template_string(LOGIN_TEMPLATE, error=None)


@app.route("/logout")
def logout():
    clear_credentials()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    api_key, api_secret = get_credentials()
    if not api_key or not api_secret:
        return redirect(url_for("login"))

    error = None
    funding_fees = []
    open_orders = []
    order_history = None
    symbol = request.args.get("symbol", "").strip().upper() or None

    # Funding fee history (no symbol required, covers all symbols)
    try:
        raw_income = binance_signed_get(
            "/fapi/v1/income", api_key, api_secret,
            {"incomeType": "FUNDING_FEE", "limit": 50},
        )
        for item in reversed(raw_income):  # newest first
            ts = int(item["time"]) / 1000
            funding_fees.append({
                "time_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
                "symbol": item.get("symbol", "-"),
                "income": item.get("income", "0"),
                "amount_val": float(item.get("income", 0)),
            })
    except Exception as e:
        error = f"ดึงข้อมูล funding fee ไม่สำเร็จ: {e}"

    # Open orders (across all symbols)
    try:
        open_orders = binance_signed_get("/fapi/v1/openOrders", api_key, api_secret)
    except Exception as e:
        msg = f"ดึงข้อมูล open orders ไม่สำเร็จ: {e}"
        error = f"{error} | {msg}" if error else msg

    # Order history for a specific symbol (Binance requires a symbol for this endpoint)
    if symbol:
        try:
            raw_orders = binance_signed_get(
                "/fapi/v1/allOrders", api_key, api_secret,
                {"symbol": symbol, "limit": 50},
            )
            order_history = []
            for o in reversed(raw_orders):
                ts = int(o["time"]) / 1000
                order_history.append({
                    "time_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
                    "side": o.get("side"),
                    "type": o.get("type"),
                    "price": o.get("price"),
                    "origQty": o.get("origQty"),
                    "status": o.get("status"),
                })
        except Exception as e:
            msg = f"ดึงประวัติคำสั่งของ {symbol} ไม่สำเร็จ: {e}"
            error = f"{error} | {msg}" if error else msg

    return render_template_string(
        DASHBOARD_TEMPLATE,
        error=error,
        funding_fees=funding_fees,
        open_orders=open_orders,
        order_history=order_history,
        symbol=symbol,
    )


if __name__ == "__main__":
    # Bind to localhost only by default — do not change host to "0.0.0.0"
    # unless you understand the exposure (anyone on that network/host could
    # reach the login form and, if debug is on, the debugger).
    app.run(host="127.0.0.1", port=5000, debug=DEBUG_MODE)
