"""Application entry point."""

from __future__ import annotations

import logging

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    uvicorn.run(
        "app.main:app",
        host=settings.analytics_host,
        port=settings.analytics_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
