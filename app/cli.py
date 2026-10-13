from __future__ import annotations

import argparse
import json
import logging
import time

from app.config import get_database_path, get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="db-analytics",
        description="Manage the db-analytics service.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialize the analytics database")

    sync_parser = subparsers.add_parser(
        "sync", help="Synchronize XAUUSD 1m candles from db-gold"
    )
    sync_parser.add_argument("--start-time", type=int)
    sync_parser.add_argument("--end-time", type=int)
    sync_parser.add_argument("--batch-size", type=int)

    subparsers.add_parser("status", help="Show local database and sync status")
    subparsers.add_parser("catalog", help="Discover available indicators")
    subparsers.add_parser("instances", help="List indicator instances")
    subparsers.add_parser("manage", help="Interactively manage indicator instances")

    activate = subparsers.add_parser("activate", help="Activate an indicator")
    activate.add_argument("--indicator-id", required=True)
    activate.add_argument("--instance-id")
    activate.add_argument("--parameters", default="{}")
    activate.add_argument("--symbol", default="XAUUSD")
    activate.add_argument("--interval", default="1m")

    for command in ("enable", "disable", "delete"):
        item = subparsers.add_parser(command, help=f"{command.title()} an instance")
        item.add_argument("instance_id")

    run = subparsers.add_parser(
        "run", help="Process all available data for an indicator instance"
    )
    run.add_argument("instance_id")
    run.add_argument("--mode", choices=("historical", "online"), default="historical")
    run.add_argument("--batch-size", type=int, default=500)

    worker = subparsers.add_parser("worker", help="Run indicator calculations continuously")
    worker.add_argument("--batch-size", type=int, default=500)
    worker.add_argument("--interval-seconds", type=float, default=5.0)

    return parser


def _print(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _manage_interactively() -> int:
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

        print("\n=== Indicator management ===")
        print("Available algorithms:")
        for index, item in enumerate(catalog, 1):
            print(f"  A{index}. {item['identifier']} — {item['display_name']}")

        print("\nInstances:")
        for index, item in enumerate(instances, 1):
            print(
                f"  {index}. {item['instance_id']} | {item['status']} | "
                f"{item['parameters']} | historical={item['historical_status']}"
            )

        print("\n[a] activate  [e] enable  [d] disable  [x] delete  [q] quit")
        choice = input("Choose: ").strip().lower()

        if choice == "q":
            return 0
        if choice == "a":
            if not catalog:
                print("No indicators discovered.")
                continue
            number = input("Algorithm number (A-number): ").strip().upper()
            if not number.startswith("A") or not number[1:].isdigit():
                print("Invalid algorithm selection.")
                continue
            index = int(number[1:]) - 1
            if not 0 <= index < len(catalog):
                print("Selection out of range.")
                continue

            item = catalog[index]
            raw = input(
                f"Parameters JSON {item['default_parameters']}: "
            ).strip()
            try:
                parameters = json.loads(raw) if raw else item["default_parameters"]
                _print(activate_indicator(
                    item["identifier"], parameters=parameters
                ))
            except (ValueError, json.JSONDecodeError) as exc:
                print(f"Error: {exc}")
            continue

        if choice in {"e", "d", "x"}:
            if not instances:
                print("No instances.")
                continue
            raw_index = input("Instance number: ").strip()
            if not raw_index.isdigit():
                print("Invalid selection.")
                continue
            index = int(raw_index) - 1
            if not 0 <= index < len(instances):
                print("Selection out of range.")
                continue

            instance_id = instances[index]["instance_id"]
            try:
                if choice == "x":
                    confirm = input(f"Delete {instance_id}? [y/N]: ").strip().lower()
                    if confirm == "y":
                        _print(delete_instance(instance_id))
                else:
                    _print(set_instance_status(
                        instance_id, "active" if choice == "e" else "disabled"
                    ))
            except ValueError as exc:
                print(f"Error: {exc}")
            continue

        print("Unknown option.")


def main() -> int:
    args = build_parser().parse_args()
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.command == "init":
        from app.database.core import initialize_configured
        initialize_configured()
        _print({"status": "initialized"})
        return 0

    if args.command == "sync":
        from app.sync_service import sync_candles
        result = sync_candles(
            start_time=args.start_time,
            end_time=args.end_time,
            batch_size=args.batch_size,
        )
        _print(result)
        return 0

    if args.command == "status":
        from app.database.core import connect
        database_path = get_database_path()
        if not database_path.exists():
            _print({
                "database_exists": False,
                "database_path": str(database_path),
                "candle_count": 0,
                "latest_candle_time": None,
                "latest_sync": None,
            })
            return 0

        with connect(database_path) as connection:
            candle_count = connection.execute(
                "SELECT COUNT(*) FROM candles WHERE symbol='XAUUSD' AND interval='1m'"
            ).fetchone()[0]
            latest_candle = connection.execute(
                "SELECT MAX(candle_time) FROM candles WHERE symbol='XAUUSD' AND interval='1m'"
            ).fetchone()[0]
            latest_sync = connection.execute("""
                SELECT run_id, status, started_at, completed_at,
                       fetched_count, inserted_or_updated_count, error_details
                FROM sync_runs ORDER BY started_at DESC LIMIT 1
            """).fetchone()

        _print({
            "database_exists": True,
            "database_path": str(database_path),
            "candle_count": candle_count,
            "latest_candle_time": latest_candle,
            "latest_sync": dict(latest_sync) if latest_sync else None,
        })
        return 0

    if args.command in {"catalog", "instances", "manage", "activate",
                        "enable", "disable", "delete", "run", "worker"}:
        from app.database.core import initialize_configured
        from app.indicators.lifecycle import (
            activate_indicator,
            delete_instance,
            discover_indicators,
            list_instances,
            run_instance_batch,
            set_instance_status,
        )

        initialize_configured()

        if args.command == "catalog":
            _print(discover_indicators())
            return 0
        if args.command == "instances":
            _print(list_instances())
            return 0
        if args.command == "manage":
            return _manage_interactively()
        if args.command == "activate":
            try:
                parameters = json.loads(args.parameters)
                if not isinstance(parameters, dict):
                    raise ValueError("--parameters must be a JSON object")
                _print(activate_indicator(
                    args.indicator_id,
                    instance_id=args.instance_id,
                    parameters=parameters,
                    symbol=args.symbol,
                    interval=args.interval,
                ))
                return 0
            except (ValueError, json.JSONDecodeError) as exc:
                logging.error("%s", exc)
                return 2
        if args.command == "enable":
            _print(set_instance_status(args.instance_id, "active"))
            return 0
        if args.command == "disable":
            _print(set_instance_status(args.instance_id, "disabled"))
            return 0
        if args.command == "delete":
            _print(delete_instance(args.instance_id))
            return 0
        if args.command == "run":
            if args.batch_size < 1:
                logging.error("Batch size must be positive.")
                return 2

            total_processed = 0
            total_saved = 0
            batches = 0
            last_checkpoint = None

            while True:
                result = run_instance_batch(
                    args.instance_id,
                    mode=args.mode,
                    batch_size=args.batch_size,
                )
                batches += 1
                total_processed += result.get("processed_count", 0)
                total_saved += result.get("saved_value_count", 0)
                last_checkpoint = result.get("checkpoint_time")

                if result.get("processed_count", 0) == 0:
                    break

            _print({
                "instance_id": args.instance_id,
                "mode": args.mode,
                "batches": batches,
                "processed_count": total_processed,
                "saved_value_count": total_saved,
                "checkpoint_time": last_checkpoint,
                "completed": True,
            })
            return 0
        if args.command == "worker":
            if args.batch_size < 1 or args.interval_seconds <= 0:
                logging.error("Batch size and interval must be positive.")
                return 2
            logging.info("Indicator worker started. Press Ctrl+C to stop.")
            try:
                while True:
                    for instance in list_instances():
                        if instance["status"] != "active":
                            continue
                        mode = (
                            "historical"
                            if instance["historical_status"] != "completed"
                            else "online"
                        )
                        try:
                            result = run_instance_batch(
                                instance["instance_id"],
                                mode=mode,
                                batch_size=args.batch_size,
                            )
                            logging.info("%s", json.dumps(result, ensure_ascii=False))
                        except Exception:
                            logging.exception(
                                "Indicator batch failed: %s",
                                instance["instance_id"],
                            )
                    time.sleep(args.interval_seconds)
            except KeyboardInterrupt:
                logging.info("Indicator worker stopped.")
                return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
