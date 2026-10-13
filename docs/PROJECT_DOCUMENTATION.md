# مستندات جامع پروژه db-analytics

## 1. معرفی پروژه

`db-analytics` یک سرویس مستقل برای ذخیره‌سازی و تحلیل داده‌های کندل `XAUUSD` در بازه زمانی `1m` است. سرویس از `SQLite` برای نگهداری داده‌ها، `FastAPI` برای ارائه API و یک Worker داخلی برای همگام‌سازی کندل‌ها و محاسبه اندیکاتورها استفاده می‌کند.

اهداف اصلی:

- دریافت و همگام‌سازی کندل‌ها از سرویس `db-gold`.
- نگهداری داده‌های بازار در Database محلی.
- کشف و ثبت Indicator implementations.
- ساخت و مدیریت Indicator instances با پارامترهای مشخص.
- پردازش تاریخی و آنلاین اندیکاتورها.
- ارائه API برای مشاهده کندل‌ها، وضعیت همگام‌سازی و نتایج اندیکاتورها.
- فراهم‌کردن CLI برای عملیات مدیریتی و عیب‌یابی.

این پروژه لایه تحلیل مستقل است؛ ارتباط با منبع داده از طریق Client و تنظیمات تعریف‌شده در پروژه انجام می‌شود.

## 2. ساختار پروژه

ساختار مهم فعلی:

```text
/opt/db-analytics/
├── app/
│   ├── server.py
│   ├── main.py
│   ├── cli.py
│   ├── config.py
│   ├── sync_service.py
│   ├── worker.py
│   ├── clients/
│   │   └── db_gold.py
│   ├── database/
│   │   └── core.py
│   └── indicators/
│       ├── base.py
│       ├── candle_loader.py
│       ├── engine.py
│       ├── lifecycle.py
│       ├── ma.py
│       ├── registry.py
│       ├── results.py
│       ├── rsi.py
│       ├── service.py
│       └── active/
├── docs/
│   └── ADDING_INDICATORS.md
├── tests/
├── data/
├── install.sh
├── pyproject.toml
└── README.md
```

فهرست بالا اجزای اصلی شناخته‌شده را نشان می‌دهد؛ فایل‌های کمکی، فایل‌های محلی و فایل‌های تولیدشده ممکن است در آن نمایش داده نشده باشند.

## 3. مسئولیت ماژول‌ها

### `app/server.py`

نقطه ورود اجرای HTTP server است. تنظیمات برنامه را می‌خواند، Logging را پیکربندی می‌کند و Uvicorn را با `app.main:app` اجرا می‌کند.

### `app/main.py`

برنامه FastAPI، endpointهای HTTP و چرخه عمر Worker را تعریف می‌کند. بخش‌های مربوط به کندل‌ها، همگام‌سازی و Indicator API در این ماژول قرار دارند.

### `app/config.py`

تنظیمات برنامه را با `pydantic-settings` مدیریت می‌کند. تابع `get_settings()` تنظیمات را به‌صورت Cache‌شده ارائه می‌کند و `get_database_path()` مسیر نهایی Database را تعیین می‌کند.

### `app/clients/db_gold.py`

Client ارتباط با API منبع `db-gold` است. جزئیات قرارداد درخواست‌ها و پاسخ‌ها باید از پیاده‌سازی همین ماژول بررسی شوند.

### `app/sync_service.py`

مسئولیت همگام‌سازی کندل‌ها با منبع داده را بر عهده دارد. عملیات همگام‌سازی می‌تواند از CLI، API یا Worker فراخوانی شود.

### `app/database/core.py`

مسئول اتصال و آماده‌سازی Database است. توابع عمومی این ماژول، از جمله `connect`، `connect_configured`، `initialize` و `initialize_configured`، در بخش‌های مختلف برنامه استفاده می‌شوند.

### `app/indicators/base.py`

قرارداد پایه Indicator، ساختار metadata، ورودی کندل و خروجی محاسبات را تعریف می‌کند.

### `app/indicators/registry.py`

مسئول ثبت metadata و مجموعه پارامترهای Indicator در Registry و Database است.

### `app/indicators/lifecycle.py`

عملیات چرخه عمر Indicator instances، شامل کشف، ایجاد، فهرست‌کردن، تغییر وضعیت، حذف و اجرای batch را فراهم می‌کند.

### `app/indicators/engine.py`

جزئیات اجرای محاسبات Indicator در این بخش قرار دارند. رفتار دقیق باید بر اساس پیاده‌سازی جاری و آزمون‌های مربوطه بررسی شود.

### `app/indicators/candle_loader.py`

بخش مرتبط با آماده‌سازی و بارگذاری کندل‌ها برای پردازش Indicator است.

### `app/indicators/results.py`

امکان پرس‌وجو و بازیابی مقادیر محاسبه‌شده Indicator را فراهم می‌کند.

### Indicator implementations

- `app/indicators/ma.py`: پیاده‌سازی Moving Average.
- `app/indicators/rsi.py`: پیاده‌سازی Relative Strength Index.

فایل‌های implementation باید از فایل‌های instance configuration جدا بمانند.

### `app/worker.py`

چرخه پردازش پس‌زمینه را اجرا می‌کند. Worker همگام‌سازی دوره‌ای کندل‌ها و پردازش batch مربوط به instanceهای فعال را انجام می‌دهد.

### `app/cli.py`

رابط خط فرمان برای آماده‌سازی Database، همگام‌سازی، مشاهده وضعیت، کشف Indicatorها، مدیریت instanceها و اجرای محاسبات است.

## 4. معماری و جریان داده

جریان اصلی داده:

```text
db-gold API
    |
    v
DbGold Client
    |
    v
Sync Service
    |
    v
SQLite Database
    |
    v
Candle Loader / Indicator Engine
    |
    v
Indicator Results
    |
    v
API / CLI
```

چرخه پس‌زمینه:

```text
FastAPI Lifespan
    |
    v
analytics-worker thread
    |
    +--> Periodic candle synchronization
    |
    +--> Read indicator instances
              |
              v
        Active instances
              |
              v
        Historical or Online batches
              |
              v
        Persisted indicator values
```

این نمودار نمای کلی مسئولیت‌هاست؛ ترتیب دقیق فراخوانی‌ها و جزئیات ذخیره‌سازی باید از کد هر ماژول استخراج شود.

## 5. تنظیمات

تنظیمات در `app/config.py` تعریف شده‌اند.

| Setting | مقدار پیش‌فرض | کاربرد |
|---|---|---|
| `DB_GOLD_API_BASE_URL` | `http://127.0.0.1:8000` | آدرس API منبع داده |
| `ANALYTICS_DATABASE_PATH` | `data/analytics.db` | مسیر Database |
| `ANALYTICS_HOST` | `127.0.0.1` | آدرس Bind سرویس |
| `ANALYTICS_PORT` | `8001` | پورت HTTP |
| `HTTP_TIMEOUT_SECONDS` | `10.0` | Timeout درخواست HTTP |
| `SYNC_BATCH_SIZE` | `500` | اندازه پیش‌فرض batch همگام‌سازی |
| `LOG_LEVEL` | `INFO` | سطح Logging |
| `INDICATOR_PATHS` | `app/indicators` | مسیرهای پیکربندی‌شده برای Indicator discovery |
| `SCRIPT_PATHS` | `scripts` | مسیر پیکربندی‌شده برای اسکریپت‌ها |

مقادیر نهایی ممکن است با Environment یا فایل `.env` تغییر کنند. مقادیر Environment باید با نام‌گذاری مورد انتظار `pydantic-settings` مطابقت داشته باشند.

مسیرهای نسبی Database نسبت به ریشه پروژه محاسبه می‌شوند.

فایل `.env` نباید حاوی Secretهای واقعی باشد که در Git منتشر شوند.

## 6. Database و داده‌های کندل

Database پیش‌فرض:

`/opt/db-analytics/data/analytics.db`

این مسیر فقط مقدار پیش‌فرض است؛ مسیر مؤثر را با تنظیمات جاری بررسی کنید.

جدول `candles` در کد فعلی با فیلدهای زیر استفاده می‌شود:

- `symbol`
- `interval`
- `candle_time`
- `open`
- `high`
- `low`
- `close`
- `tick_volume`
- `spread`
- `real_volume`

برای سری پیش‌فرض پروژه، `symbol=XAUUSD` و `interval=1m` است.

جدول `sync_runs` برای ثبت اطلاعات اجرای همگام‌سازی استفاده می‌شود. اطلاعات قابل مشاهده شامل `run_id`، `status`، زمان شروع و پایان، تعداد داده‌های دریافت‌شده و درج یا به‌روزرسانی‌شده و جزئیات خطا است.

ساختار کامل Schema، محدودیت‌ها، Indexها و Migrationهای واقعی باید از `app/database/core.py` و Database جاری استخراج شوند؛ این سند جایگزین Schema مرجع نیست.

## 7. همگام‌سازی کندل‌ها

همگام‌سازی از طریق تابع `sync_candles()` در `app/sync_service.py` انجام می‌شود.

روش‌های فراخوانی:

- CLI با دستور `sync`.
- API با `POST /api/v1/sync`.
- Worker داخلی به‌صورت دوره‌ای.

پارامترهای CLI:

- `--start-time`: زمان شروع اختیاری.
- `--end-time`: زمان پایان اختیاری.
- `--batch-size`: اندازه batch اختیاری.

در API نیز پارامترهای `start_time`، `end_time` و `batch_size` وجود دارند. مقادیر محدودشده در API باید مطابق تعریف endpoint باشند.

برای بررسی آخرین وضعیت همگام‌سازی از `GET /api/v1/sync-runs` یا دستور CLI `status` استفاده کنید.

وجود خطا در یک اجرای همگام‌سازی لزوماً به معنی از کار افتادن کل سرویس نیست؛ نتیجه و Log همان اجرا باید بررسی شود.

## 8. Indicator architecture

### قرارداد implementation

هر Indicator باید از `Indicator` در `app/indicators/base.py` ارث‌بری کند و موارد زیر را پیاده‌سازی کند:

- `metadata`
- `calculate(candles, parameters)`

Metadata شامل شناسه یکتا، نام نمایشی، نسخه پیاده‌سازی، توضیح، پارامترهای پیش‌فرض و `required_lookback` است.

ورودی محاسبه شامل دنباله‌ای از `CandleInput` و پارامترهاست. خروجی شامل `IndicatorOutput`های متناظر با زمان کندل‌هاست.

قواعد مهم:

- پارامترهای ناشناخته یا نامعتبر باید به‌روشنی رد شوند.
- رفتار Warm-up و تاریخچه ناکافی باید مشخص باشد.
- ترتیب زمانی خروجی حفظ شود.
- محاسبات برای ورودی و پارامتر یکسان تکرارپذیر باشند.
- منطق Indicator نباید بدون نیاز به شبکه یا API خارجی وابسته شود.
- تغییر فرمولی که نتایج را عوض می‌کند باید با نسخه‌بندی implementation مدیریت شود.

### Discovery و Registry

Discovery، implementationهای واجد شرایط را از مسیرهای پیکربندی‌شده شناسایی می‌کند. Registry metadata و مجموعه پارامترها را ثبت می‌کند.

ثبت metadata به‌تنهایی معادل اجرای محاسبات نیست. برای استفاده از Indicator باید مسیر discovery، ثبت، ایجاد instance و پردازش آن موفق باشد.

### Instance

Instance نماینده یک Indicator با پارامترها و تنظیمات مشخص است.

اطلاعات instance می‌تواند شامل موارد زیر باشد:

- `instance_id`
- `indicator_id`
- `parameters`
- `symbol`
- `interval`
- `status`
- `historical_status`
- `historical_checkpoint_time`
- `online_checkpoint_time`
- `last_error`

فیلدهای دقیق خروجی تابع `list_instances()` و API مرجع نهایی قرارداد اجرایی هستند.

Instance configuration در مسیر زیر نگهداری می‌شود:

`app/indicators/active/<instance_id>/config.json`

این مسیر برای تنظیمات instance است؛ فایل Python مربوط به implementation نباید در این دایرکتوری قرار بگیرد.

### Historical و Online

در Worker، اگر `historical_status` یک instance برابر `completed` نباشد، ابتدا حالت `historical` انتخاب می‌شود. پس از تکمیل تاریخچه، حالت `online` انتخاب می‌شود.

پردازش با batch انجام می‌شود و checkpointها برای پیگیری پیشرفت استفاده می‌شوند.

وضعیت `active` به معنی مجاز بودن پردازش instance است؛ به‌تنهایی تضمین نمی‌کند که محاسبات بدون خطا انجام شده یا Worker در حال اجراست.

## 9. Worker و چرخه عمر سرویس

در `app/main.py` یک FastAPI lifespan وجود دارد که به‌طور پیش‌فرض Worker را در threadی با نام `analytics-worker` اجرا می‌کند.

رفتار فعلی `app/worker.py`:

- آماده‌سازی Database هنگام شروع Worker.
- تلاش برای همگام‌سازی کندل‌ها با فاصله زمانی حدود ۶۰ ثانیه.
- بررسی instanceها در چرخه‌های پردازش.
- پردازش instanceهای دارای وضعیت `active`.
- استفاده از batch size برابر ۵۰۰ در Worker داخلی.
- انتظار حدود ۵ ثانیه میان چرخه‌ها.
- ثبت نتیجه‌ها و خطاها در Logging.
- درخواست توقف از طریق `threading.Event`.
- تلاش برای Join کردن thread هنگام خاموش‌شدن FastAPI، با Timeout ده ثانیه.

اگر آماده‌سازی Database در شروع Worker شکست بخورد، Worker خطا را ثبت کرده و خارج می‌شود. بنابراین روشن بودن API به‌تنهایی تضمین نمی‌کند Worker پس از شروع همچنان سالم باشد.

در آزمون‌های API، `app.state.disable_worker` برای جلوگیری از اجرای Worker پس‌زمینه در `TestClient` استفاده می‌شود.

### systemd

Unit فعلی:

`/etc/systemd/system/db-analytics.service`

تنظیمات مهم مشاهده‌شده:

- User: `unit2`
- Working directory: `/opt/db-analytics`
- Environment file: `/opt/db-analytics/.env`
- اجرای برنامه: `/opt/db-analytics/.venv/bin/python -m app.server`
- سیاست Restart: `on-failure`
- Restart delay: پنج ثانیه

این Unit سرویس API و در نتیجه میزبان Worker داخلی را اجرا می‌کند؛ Unit جداگانه‌ای برای Worker در بررسی فعلی مشاهده نشده است.

## 10. API reference

آدرس پایه در تنظیمات فعلی معمولاً:

`http://127.0.0.1:8001`

### Health

`GET /health`

وضعیت HTTP API و وضعیت چرخه عمر Worker داخلی را گزارش می‌کند. پاسخ موفق شامل `status=ok`، `service=db-analytics` و `worker_state` است. مقدار `worker_state` وضعیت thread را منعکس می‌کند؛ `running` به‌تنهایی موفقیت همه چرخه‌های پردازش را تضمین نمی‌کند. برای تأیید عملکرد واقعی، Logهای سرویس، نتیجه آخرین Sync، checkpointهای Indicatorها و `last_error` را نیز بررسی کنید.

### Candles

`GET /api/v1/candles`

پارامترها:

- `limit`: تعداد حداکثر رکوردهای برگشتی، بین ۱ تا ۱۰۰۰؛ پیش‌فرض ۱۰۰.
- `start_time`: مرز زمانی پایین، شامل خود زمان.
- `end_time`: مرز زمانی بالا، شامل خود زمان.
- `symbol`: فقط `XAUUSD` پشتیبانی می‌شود.
- `interval`: فقط `1m` پشتیبانی می‌شود.

پاسخ شامل نماد، بازه زمانی، تعداد کل رکوردهای منطبق، تعداد رکوردهای برگشتی و آرایه کندل‌هاست. کندل‌ها به ترتیب زمانی صعودی در خروجی قرار می‌گیرند.

`GET /api/v1/candles/latest`

آخرین کندل موجود را برمی‌گرداند. اگر کندلی موجود نباشد، پاسخ `404` است.

### Synchronization

`GET /api/v1/sync-runs`

آخرین اجراهای همگام‌سازی را برمی‌گرداند. پارامتر `limit` بین ۱ تا ۱۰۰ است و پیش‌فرض آن ۲۰ است.

`POST /api/v1/sync`

همگام‌سازی را به‌صورت درخواست مستقیم اجرا می‌کند. پارامترهای اختیاری شامل `start_time`، `end_time` و `batch_size` هستند. خطاهای `ValueError` و `RuntimeError` به پاسخ `502` تبدیل می‌شوند.

### Indicator endpoints

| Method | Endpoint | کاربرد |
|---|---|---|
| `GET` | `/api/v1/indicators/catalog` | مشاهده کاتالوگ Indicatorها |
| `GET` | `/api/v1/indicators/instances` | فهرست instanceها |
| `POST` | `/api/v1/indicators/instances` | ایجاد instance |
| `PATCH` | `/api/v1/indicators/instances/{instance_id}` | تغییر وضعیت instance |
| `DELETE` | `/api/v1/indicators/instances/{instance_id}` | حذف instance |
| `POST` | `/api/v1/indicators/instances/{instance_id}/run` | اجرای پردازش instance |
| `GET` | `/api/v1/indicators/instances/{instance_id}/values` | مشاهده مقادیر محاسبه‌شده |

### ایجاد instance

نمونه درخواست:

```json
{
  "indicator_id": "moving_average",
  "parameters": {
    "period": 20
  },
  "symbol": "XAUUSD",
  "interval": "1m"
}
```

`instance_id` اختیاری است. در صورت حذف آن، برنامه می‌تواند بر اساس شناسه Indicator و پارامترهای resolved یک شناسه تولید کند.

شناسه Indicator باید با implementation شناخته‌شده مطابقت داشته باشد.

### اجرای instance

درخواست:

`POST /api/v1/indicators/instances/{instance_id}/run`

پارامترها:

- `mode`: یکی از `historical` یا `online`؛ پیش‌فرض `historical`.
- `batch_size`: عددی بین ۱ تا ۱۰۰۰۰؛ پیش‌فرض ۵۰۰.

### مشاهده مقادیر

درخواست:

`GET /api/v1/indicators/instances/{instance_id}/values`

پارامترهای اختیاری:

- `start_time`
- `end_time`
- `output_name`
- `limit`، بین ۱ تا ۱۰۰۰۰ و با پیش‌فرض ۱۰۰۰.

`start_time` نباید از `end_time` بزرگ‌تر باشد. Instance ناشناخته می‌تواند پاسخ `404` ایجاد کند. مقدار `null` در دوره Warm-up ممکن است در خروجی وجود داشته باشد.

برای جزئیات دقیق Schema، نوع داده و همه پاسخ‌های خطا، کد endpointها در `app/main.py` مرجع نهایی است.

## 11. CLI reference

اجرای CLI از ریشه پروژه:

```bash
cd /opt/db-analytics
.venv/bin/python -m app.cli --help
```

دستورهای موجود:

| Command | کاربرد |
|---|---|
| `init` | آماده‌سازی Database |
| `sync` | همگام‌سازی کندل‌ها |
| `status` | نمایش وضعیت Database و آخرین Sync |
| `catalog` | کشف و نمایش Indicator implementations |
| `instances` | نمایش instanceها |
| `manage` | مدیریت تعاملی instanceها |
| `activate` | ایجاد و فعال‌سازی instance |
| `enable` | فعال‌کردن instance |
| `disable` | غیرفعال‌کردن instance |
| `delete` | حذف instance |
| `run` | پردازش instance در حالت مشخص |
| `worker` | اجرای حلقه محاسباتی CLI به‌صورت پیوسته |

نمونه‌ها:

```bash
.venv/bin/python -m app.cli init
.venv/bin/python -m app.cli sync
.venv/bin/python -m app.cli status
.venv/bin/python -m app.cli catalog
.venv/bin/python -m app.cli instances
.venv/bin/python -m app.cli activate \
  --indicator-id moving_average \
  --parameters '{"period":5}'
.venv/bin/python -m app.cli run moving_average_period5 \
  --mode historical
```

شناسه `moving_average_period5` در مثال آخر فقط زمانی معتبر است که instance با همین شناسه واقعاً ایجاد شده باشد.

`status` اطلاعات Database، تعداد کندل‌ها، آخرین زمان کندل، آخرین اجرای Sync، دسترسی API، وضعیت Worker، کاتالوگ Indicatorها و وضعیت instanceها را در یک خروجی JSON گزارش می‌کند. فیلد `worker_state` وضعیت مشاهده‌شده thread را نشان می‌دهد و جایگزین بررسی Logها و پیشرفت واقعی پردازش نیست. اگر API در دسترس نباشد، وضعیت آن و Worker ممکن است به‌صورت unreachable یا unknown گزارش شود.

دستور `worker` در CLI نیز حلقه‌ای مستقل اجرا می‌کند؛ با Worker داخلی FastAPI یکی نیست و نباید هم‌زمان و بدون بررسی عملیاتی اجرا شود، زیرا ممکن است دو چرخه پردازش هم‌پوشان ایجاد کند.

## 12. نصب و راه‌اندازی

پیش‌نیازهای اصلی:

- Python 3.12 یا بالاتر.
- دسترسی به API منبع `db-gold`.
- دسترسی به مسیرهای پروژه و Database.
- نصب وابستگی‌های تعریف‌شده در پروژه.

ساخت محیط مجازی و نصب وابستگی‌ها:

```bash
cd /opt/db-analytics
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
```

در صورت استفاده از نصب‌کننده رسمی پروژه، ابتدا محتوای `install.sh` را بررسی کنید و سپس مطابق روش استقرار تأییدشده اجرا کنید.

ساخت فایل تنظیمات محلی، در صورتی که نمونه تنظیمات در checkout موجود باشد:

```bash
cp .env.example .env
```

پس از تنظیم آدرس منبع داده و مسیر Database:

```bash
.venv/bin/python -m app.cli init
.venv/bin/python -m app.cli status
```

برای اجرای دستی سرویس:

```bash
.venv/bin/python -m app.server
```

اجرای جایگزین:

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
```

در اجرای Uvicorn، Host و Port باید با تنظیمات محیط مقصد هماهنگ باشند. برای استفاده عملیاتی از اجرای systemd موجود، وضعیت Unit و تنظیمات واقعی سرور را بررسی کنید.

## 13. آزمون و کنترل کیفیت

وابستگی‌های تست در گروه اختیاری `test` در `pyproject.toml` تعریف شده‌اند.

اجرای آزمون‌ها:

```bash
cd /opt/db-analytics
.venv/bin/python -m compileall -q app
.venv/bin/python -m app.cli --help
.venv/bin/pytest
```

آزمون‌ها در پوشه `tests/` قرار دارند و شامل بخش‌هایی از موارد زیر هستند:

- API
- تنظیمات
- Database
- Client منبع داده
- قرارداد پایه Indicator
- Registry
- نتایج Indicator
- همگام‌سازی
- RSI

پس از هر تغییر، ابتدا تست مرتبط و سپس مجموعه تست کامل اجرا شود. موفقیت تست‌ها باید از خروجی واقعی آزمون‌ها تأیید شود.

## 14. عیب‌یابی و عملیات

### بررسی وضعیت systemd

```bash
systemctl status db-analytics.service --no-pager
```

### مشاهده Logهای سرویس

```bash
journalctl -u db-analytics.service -n 200 --no-pager
```

برای مشاهده زنده:

```bash
journalctl -u db-analytics.service -f
```

### بررسی API

```bash
curl -fsS http://127.0.0.1:8001/health
```

در صورت تغییر Host یا Port، آدرس را با تنظیمات واقعی جایگزین کنید.

### بررسی Database و Sync

```bash
cd /opt/db-analytics
.venv/bin/python -m app.cli status
```

سپس آخرین اجراهای Sync را از API یا Database بررسی کنید.

### تأیید عملیاتی ثبت‌شده در 2026-10-13

پس از بارگذاری نسخه به‌روزشده، سرویس واقعی `db-analytics.service` با موفقیت Restart شد و وضعیت `active (running)` داشت. درخواست `GET /health` پاسخ HTTP 200 و `worker_state=running` برگرداند. دستور `python -m app.cli status` نیز `api_status=reachable` و `worker_state=running` را گزارش کرد. آخرین Sync دارای وضعیت `succeeded` بود و Logهای همان اجرا، پردازش Online هر دو instance فعال `moving_average_period20` و `relative_strength_index_period14` را بدون `last_error` نشان دادند.

این نتیجه، تأیید عملیاتی همان اجراست؛ وضعیت جاری باید با دستورهای بالا بررسی شود، زیرا تعداد کندل‌ها، زمان Sync و checkpointها در طول زمان تغییر می‌کنند.

### بررسی Indicatorها

```bash
.venv/bin/python -m app.cli catalog
.venv/bin/python -m app.cli instances
```

اگر instance پردازش نمی‌شود، این موارد را بررسی کنید:

1. آیا implementation در کاتالوگ دیده می‌شود؟
2. آیا instance با پارامترهای معتبر ایجاد شده است؟
3. آیا وضعیت instance برابر `active` است؟
4. آیا `historical_status` تکمیل شده است؟
5. آیا checkpointها تغییر می‌کنند؟
6. آیا `last_error` یا خطای مرتبط در Log وجود دارد؟
7. آیا Worker داخلی واقعاً شروع شده و در حال اجراست؟

وضعیت `active` به‌تنهایی اثبات سلامت Worker یا موفقیت محاسبات نیست.

## 15. توسعه Indicator جدید

راهنمای اختصاصی توسعه Indicator:

`docs/ADDING_INDICATORS.md`

پیش از افزودن implementation جدید، این راهنما و قراردادهای `app/indicators/base.py`، `registry.py` و `lifecycle.py` را مطالعه کنید.

چک‌لیست:

- [ ] فایل implementation در مسیر مورداعتماد پروژه قرار گرفته است.
- [ ] کلاس از `Indicator` ارث‌بری می‌کند.
- [ ] Metadata و identifier یکتا هستند.
- [ ] پارامترها اعتبارسنجی می‌شوند.
- [ ] فرمول و `required_lookback` صحیح‌اند.
- [ ] Warm-up و تاریخچه ناکافی مدیریت می‌شوند.
- [ ] آزمون‌های عددی مستقل و آزمون‌های مرزی اضافه شده‌اند.
- [ ] Discovery و Registry با implementation سازگارند.
- [ ] Instance از مسیر رسمی ایجاد شده است.
- [ ] پردازش تاریخی و آنلاین بررسی شده است.
- [ ] مقادیر خروجی و Logها بررسی شده‌اند.
- [ ] مستندات و نسخه implementation به‌روز هستند.

## 16. امنیت و نگهداری

- فایل `.env` و اطلاعات محرمانه نباید در Git منتشر شوند.
- اجرای implementationهای ناشناس یا بارگذاری فایل‌های Python خارج از مسیر مورداعتماد مجاز نیست.
- قبل از تغییر Database، مسیر واقعی و اثر عملیات را بررسی کنید.
- قبل از حذف instance یا فایل، Reference Audit انجام دهید.
- فایل‌های backup و تغییرات محلی Git بدون بررسی حذف یا بازنویسی نشوند.
- تغییرات باید کوچک، قابل بررسی و سازگار با قراردادهای قبلی باشند.
- منطق مشترک باید در لایه موجود استفاده شود؛ از ایجاد مسیرهای محاسباتی موازی و تکراری خودداری کنید.

## 17. وضعیت و محدودیت‌های مستندات

این سند بر اساس کد و خروجی‌های بررسی‌شده تهیه شده است. موارد زیر باید هنگام تغییر سیستم بازبینی شوند:

- تغییر Schema یا روش Migration در Database.
- تغییر قرارداد API یا CLI.
- تغییر روش Discovery و Registry.
- تغییر رفتار Worker یا زمان‌بندی Sync.
- تغییر تنظیمات استقرار systemd.
- اضافه‌شدن Indicator یا تغییر فرمول و نسخه آن.
- تغییر روش ذخیره‌سازی و بازیابی نتایج.

برای جزئیات دقیق پیاده‌سازی، کد جاری و آزمون‌های آن مرجع نهایی هستند. هرگاه رفتار واقعی کد با این سند تفاوت داشت، ابتدا اختلاف را بررسی کنید و سپس کد یا مستندات را به‌صورت کنترل‌شده اصلاح کنید.
