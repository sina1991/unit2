# db-analytics

سرویس تحلیل داده‌های کندل XAUUSD با پایگاه داده SQLite، رابط HTTP مبتنی بر FastAPI و محاسبه‌ی خودکار اندیکاتورها.
## پیش‌نیازها

* Python 3.12 یا بالاتر
* در دسترس بودن API منبع `db-gold` برای همگام‌سازی کندل‌ها

## نصب و راه‌اندازی

ساخت محیط مجازی و نصب وابستگی‌ها:

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
