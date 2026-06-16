import logging
import signal
from threading import Event

from app.worker.config import load_worker_config
from app.worker.runner import run_forever


def main() -> None:
    config = load_worker_config()
    logging.basicConfig(
        level=getattr(logging, _log_level(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    stop_event = Event()

    def _stop(signum, frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    run_forever(config=config, stop_event=stop_event)


def _log_level() -> str:
    import os

    return os.getenv("WORKER_LOG_LEVEL", "INFO").upper()


if __name__ == "__main__":
    main()
