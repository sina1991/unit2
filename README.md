# db-analytics

سرویس تحلیل داده‌های کندل XAUUSD با پایگاه داده SQLite، رابط HTTP مبتنی بر FastAPI و محاسبه‌ی خودکار اندیکاتورها.
## پیش‌نیازها

* Python 3.12 یا بالاتر
* در دسترس بودن API منبع `db-gold` برای همگام‌سازی کندل‌ها

## نصب و راه‌اندازی

ساخت محیط مجازی و نصب وابستگی‌ها:

```bash
curl -fsSL https://raw.githubusercontent.com/sina1991/unit2/feature/core-implementation/install.sh | sudo bash
```

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

ساخت فایل تنظیمات محلی:

```bash
cp .env.example .env
```

آدرس پیش‌فرض API منبع `http://127.0.0.1:8000` است. در صورت نیاز، مقادیر فایل `.env` را تغییر بده.
آماده‌سازی پایگاه داده و همگام‌سازی اولیه:

```bash
.venv/bin/python -m app.cli init
.venv/bin/python -m app.cli sync
.venv/bin/python -m app.cli status
```

داده‌ها به‌طور پیش‌فرض در `data/analytics.db` ذخیره می‌شوند. فایل `.env`، پایگاه داده و محیط مجازی از Git مستثنا هستند.
## اجرای سرویس

برای اجرای سرویس:

```bash
.venv/bin/python -m app.server
```

روش جایگزین با Uvicorn:

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
```

آدرس پیش‌فرض API برابر `http://127.0.0.1:8001` است. مستندات تعاملی API در `http://127.0.0.1:8001/docs` در دسترس است.

worker داخلی هنگام شروع FastAPI فعال می‌شود و هنگام خاموش‌شدن سرویس، درخواست توقف دریافت می‌کند.
## کنترل کیفیت

برای بررسی کد و اجرای تست‌ها:

```bash
.venv/bin/python -m compileall -q app
.venv/bin/python -m app.cli --help
.venv/bin/pytest
```
## Indicator Discovery, Lifecycle, and API

## Indicator Discovery, Lifecycle, and API

### 1. Indicator discovery

The lifecycle module discovers indicator implementations from the directories
configured by `indicator_paths` in the application settings.

Discovery recursively scans Python files and skips infrastructure modules,
files inside `active` directories, and `__pycache__` directories. A discovered
implementation must be a concrete subclass of `Indicator` and expose valid
metadata.

Each indicator should provide:
- A unique `metadata.identifier`
- A display name, implementation version, and description
- Default parameters and a required lookback
- A `calculate()` implementation returning `IndicatorOutput` objects

The runtime loads an implementation by its metadata identifier. Adding a new
indicator normally requires adding its Python implementation to a configured
discovery directory; a separate route in `app/main.py` is not required.

### 2. Indicator lifecycle

Creating an instance through `activate_indicator()` validates the requested
parameters, registers the indicator and parameter set in the database, creates
an instance directory under `app/indicators/active/`, writes `config.json`,
and persists the instance record.

The default symbol is `XAUUSD` and the default interval is `1m`. A newly
created instance starts with `status: active` and
`historical_status: pending`.

Instance IDs may contain letters, numbers, underscores, and hyphens, with a
maximum length of 100 characters.

### 3. Indicator API endpoints

| Purpose | Method and endpoint |
|---|---|
| Health check | `GET /health` |
| List discovered indicators | `GET /api/v1/indicators/catalog` |
| List indicator instances | `GET /api/v1/indicators/instances` |
| Create an instance | `POST /api/v1/indicators/instances` |
| Change instance status | `PATCH /api/v1/indicators/instances/{instance_id}` |
| Delete an instance | `DELETE /api/v1/indicators/instances/{instance_id}` |
| Run an instance | `POST /api/v1/indicators/instances/{instance_id}/run` |
| Query calculated values | `GET /api/v1/indicators/instances/{instance_id}/values` |

#### List indicators

`GET /api/v1/indicators/catalog`

Returns discovered indicator metadata and each indicator's registration
status in the database.

#### List instances

`GET /api/v1/indicators/instances`

Returns persisted instances, including their stored parameters.

#### Create an instance

`POST /api/v1/indicators/instances`

Example request:

```json
{
  "indicator_id": "moving_average",
  "parameters": {
    "period": 20
  },
  "symbol": "XAUUSD",
  "interval": "1m"
}

indicator_id must match a discovered implementation. instance_id is optional; when omitted, the application generates it from the indicator identifier and resolved parameters. Successful creation returns HTTP 201.

Run an instance

POST /api/v1/indicators/instances/{instance_id}/run

Query parameters:

mode: historical or online; defaults to historical.

batch_size: integer from 1 to 10000; defaults to 500.

Query calculated values

GET /api/v1/indicators/instances/{instance_id}/values

Optional query parameters:

start_time: inclusive lower time bound.

end_time: inclusive upper time bound.

output_name: filter by output name.

limit: maximum number of rows, from 1 to 10000; defaults to 1000.

The start time must not exceed the end time. An unknown instance returns HTTP 404. Output rows can include warm-up entries whose value is null.

Change status or delete an instance

Use PATCH /api/v1/indicators/instances/{instance_id} with a JSON body such as {"status": "disabled"} or {"status": "active"}.

Use DELETE /api/v1/indicators/instances/{instance_id} to remove an instance.

4. Adding a new indicator (example: RSI)

Add an RSI implementation as a Python file in a directory included in indicator_paths.

Implement the Indicator interface, metadata, parameter validation, and calculation logic.

Add unit tests for normal values, parameter validation, and warm-up output.

Run the test suite.

Query the catalog to confirm that RSI is discovered.

Create an RSI instance through the API.

Run it in historical mode and query its calculated values.

Verify the instance status and results before relying on live processing.

Use the existing Moving Average implementation and indicator tests as references. Do not place implementation files inside app/indicators/active/; that directory stores instance configurations rather than discoverable indicator implementations. """

text = path.read_text(encoding="utf-8") if marker in text: print("این بخش از قبل در README.md وجود دارد؛ تغییری انجام نشد.") else: with path.open("a", encoding="utf-8") as f: f.write("\n" + content.lstrip()) print("بخش مستندات اندیکاتورها به README.md اضافه شد.") 
