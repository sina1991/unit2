"""Background candle synchronization and indicator calculation worker."""

from __future__ import annotations

import json
import logging
import threading
import time


def worker_loop(stop_event: threading.Event) -> None:
    from app.database.core import initialize_configured
    from app.indicators.lifecycle import list_instances, run_instance_batch
    from app.sync_service import sync_candles

    batch_size = 500
    poll_interval_seconds = 5.0
    sync_interval_seconds = 60.0
    last_sync_at = 0.0

    try:
        initialize_configured()
    except Exception:
        logging.exception("Could not initialize worker database.")
        return

    logging.info("Synchronization and indicator worker started.")

    while not stop_event.is_set():
        now = time.monotonic()

        if now - last_sync_at >= sync_interval_seconds:
            try:
                result = sync_candles()
                logging.info(
                    "Candle synchronization result: %s",
                    json.dumps(result, ensure_ascii=False, default=str),
                )
            except Exception:
                logging.exception("Automatic candle synchronization failed.")
            finally:
                last_sync_at = time.monotonic()

        try:
            for instance in list_instances():
                if stop_event.is_set():
                    break

                if instance["status"] != "active":
                    continue

                instance_id = instance["instance_id"]
                mode = (
                    "historical"
                    if instance["historical_status"] != "completed"
                    else "online"
                )

                while not stop_event.is_set():
                    try:
                        result = run_instance_batch(
                            instance_id,
                            mode=mode,
                            batch_size=batch_size,
                        )
                        logging.info(
                            "Indicator result: %s",
                            json.dumps(result, ensure_ascii=False, default=str),
                        )

                        if result.get("processed_count", 0) == 0:
                            break

                    except Exception:
                        logging.exception(
                            "Calculation failed for instance %s",
                            instance_id,
                        )
                        break

        except Exception:
            logging.exception("Indicator worker cycle failed.")

        stop_event.wait(poll_interval_seconds)

    logging.info("Synchronization and indicator worker stopped.")
