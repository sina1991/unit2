from __future__ import annotations

import argparse
import json
import logging

from app.config import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="db-analytics",
        description="Manage db analytics service",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("catalog")
    sub.add_parser("instances")
    sub.add_parser("manage")

    sync = sub.add_parser("sync")
    sync.add_argument("--start-time", type=int)
    sync.add_argument("--end-time", type=int)
    sync.add_argument("--batch-size", type=int)

    activate = sub.add_parser("activate")
    activate.add_argument("--indicator-id", required=True)
    activate.add_argument("--parameters", default="{}")
    activate.add_argument("--symbol", default="XAUUSD")
    activate.add_argument("--interval", default="1m")

    for name in ("enable", "disable", "delete"):
        cmd = sub.add_parser(name)
        cmd.add_argument("instance_id")

    run = sub.add_parser("run")
    run.add_argument("instance_id")

    worker = sub.add_parser("worker")
    worker.add_argument("--batch-size", type=int, default=500)

    return parser


def _print(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _manage_interactively():

    from app.cli_display import (
        header,
        indicators_table,
        instances_table,
    )

    from app.indicators.lifecycle import (
        activate_indicator,
        delete_instance,
        discover_indicators,
        list_instances,
        set_instance_status,
    )

    while True:

        catalog = discover_indicators()
        instances = list_instances()

        header("Indicator Management")

        indicators_table(catalog)

        instances_table(instances)

        print()
        print("[1] Activate Indicator")
        print("[2] Enable Instance")
        print("[3] Disable Instance")
        print("[4] Delete Instance")
        print("[0] Exit")

        choice = input("Choose: ").strip()

        if choice == "0":
            return 0

        if choice == "1":

            number = int(input("Indicator number: "))

            indicator = catalog[number - 1]

            params = {}

            defaults = indicator.get(
                "default_parameters",
                {}
            )

            for key, value in defaults.items():

                raw = input(
                    f"{key} [{value}]: "
                ).strip()

                if raw:
                    params[key] = int(raw)

            try:
                result = activate_indicator(
                    indicator["identifier"],
                    parameters=params,
                )

                _print(result)

            except ValueError as exc:
                print(f"Error: {exc}")


        elif choice in ("2", "3", "4"):

            number = int(
                input("Instance number: ")
            )

            instance = instances[number - 1]

            instance_id = instance["instance_id"]


            if choice == "2":
                _print(
                    set_instance_status(
                        instance_id,
                        "active"
                    )
                )

            elif choice == "3":
                _print(
                    set_instance_status(
                        instance_id,
                        "disabled"
                    )
                )

            else:
                _print(
                    delete_instance(
                        instance_id
                    )
                )


def main():

    args = build_parser().parse_args()

    settings = get_settings()

    logging.basicConfig(
        level=settings.log_level.upper()
    )


    if args.command == "manage":
        from app.database.core import initialize_configured
        initialize_configured()
        return _manage_interactively()


    from app.database.core import initialize_configured
    initialize_configured()


    if args.command == "init":

        _print(
            {
                "status": "initialized"
            }
        )
        return 0

<<<<<<< HEAD
    if args.command == "status":
        import json
        from urllib.request import urlopen

        from app.database.core import connect
        from app.indicators.lifecycle import discover_indicators, list_instances

        database_path = get_database_path()
        database_exists = database_path.exists()
        candle_count = 0
        latest_candle = None
        latest_sync = None
        instances = []

        if database_exists:
            with connect(database_path) as connection:
                candle_count = connection.execute(
                    "SELECT COUNT(*) FROM candles WHERE symbol='XAUUSD' AND interval='1m'"
                ).fetchone()[0]
                latest_candle = connection.execute(
                    "SELECT MAX(candle_time) FROM candles WHERE symbol='XAUUSD' AND interval='1m'"
                ).fetchone()[0]
                latest_sync_row = connection.execute("""
                    SELECT run_id, status, started_at, completed_at,
                           fetched_count, inserted_or_updated_count, error_details
                    FROM sync_runs ORDER BY started_at DESC LIMIT 1
                """).fetchone()
                latest_sync = dict(latest_sync_row) if latest_sync_row else None
                instances = list_instances(connection=connection)

        host = settings.analytics_host
        if host in {"0.0.0.0", "::"}:
            host = "127.0.0.1"
        health_url = f"http://{host}:{settings.analytics_port}/health"

        try:
            with urlopen(health_url, timeout=2) as response:
                health_data = json.load(response)
            api_status = "reachable"
            worker_state = health_data.get("worker_state", "unknown")
        except Exception:
            api_status = "unreachable"
            worker_state = "unknown"

        _print({
            "database_exists": database_exists,
            "database_path": str(database_path),
            "candle_count": candle_count,
            "latest_candle_time": latest_candle,
            "latest_sync": latest_sync,
            "api_status": api_status,
            "worker_state": worker_state,
            "catalog": discover_indicators(),
            "instances": instances,
        })
        return 0
=======

    if args.command == "catalog":

        from app.indicators.lifecycle import discover_indicators
>>>>>>> 655ddad (Implement plugin based indicator engine with MA EMA RSI ATR MACD)

        _print(
            discover_indicators()
        )

        return 0


    if args.command == "instances":

        from app.indicators.lifecycle import list_instances

        _print(
            list_instances()
        )

        return 0


    if args.command == "activate":

        from app.indicators.lifecycle import activate_indicator

        params=json.loads(
            args.parameters
        )

        _print(
            activate_indicator(
                args.indicator_id,
                parameters=params,
                symbol=args.symbol,
                interval=args.interval,
            )
        )

        return 0

    if args.command == "run":

        from app.indicators.lifecycle import run_instance_batch

        _print(
            run_instance_batch(
                args.instance_id
            )
        )

        return 0

    if args.command == "worker":

        import threading
        from app.worker import worker_loop

        stop_event = threading.Event()

        try:
            worker_loop(stop_event)
        except KeyboardInterrupt:
            stop_event.set()

        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
