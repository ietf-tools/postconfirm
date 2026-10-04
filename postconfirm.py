import argparse
import logging
import signal
from logging.handlers import TimedRotatingFileHandler


from anyio import create_task_group, create_tcp_listener, current_time, open_signal_receiver, run
import config

from src.milter import handle
from src.remailer import Remailer
from src.validator import Validator
from src.challenge import init_handlers as init_challenge_handlers
from src.db import close_db_pools

from src import services

async def main():
    parser = argparse.ArgumentParser(
        prog="postconfirm",
        description="Milter handler for confirming that emails come from valid email addresses"
    )
    parser.add_argument("-c", "--config-file", default="/app/etc/postconfirm.cfg", type=argparse.FileType())
    parser.add_argument("-p", "--port")

    args = parser.parse_args()

    # Load the configuration
    app_config = config.Config(args.config_file)

    log_line_format = (
        "{asctime} postconfirm/postconfirm[{process}]: {message} [{filename}:{lineno}]"
    )
    log_date_format = "%b %d %H:%M:%S"
    log_rotate_period = "D"
    log_rotate_interval = 1
    log_rotate_keep = 5
    log_filename = app_config.get(
        "log.filename", "/var/log/postconfirm/postconfirm.log"
    )
    log_level = app_config.get("log.level", logging.INFO)

    logging.basicConfig(
        level=log_level, style="{", datefmt=log_date_format, format=log_line_format
    )

    logging.getLogger("kilter.service").disabled = True

    logger = logging.getLogger()
    logger.setLevel(log_level)
    file_handler = TimedRotatingFileHandler(
        log_filename,
        when=log_rotate_period,
        interval=log_rotate_interval,
        backupCount=log_rotate_keep,
    )

    file_formatter = logging.Formatter(
        style="{", datefmt=log_date_format, fmt=log_line_format
    )

    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    #logger = logging.LoggerAdapter(logger)

    # Set up a services registry
    services["app_config"] = app_config
    services["remailer"] = Remailer(app_config)
    services["validator"] = Validator(app_config)

    init_challenge_handlers(services)

    listen_port = args.port or app_config.get("milter_port", 1999)
    drain_seconds = float(app_config.get("shutdown.drain_seconds", 20))

    # Handle signals before listening: as PID 1 in a container an unhandled
    # SIGTERM is ignored, and the pod is killed at the end of its grace period.
    with open_signal_receiver(signal.SIGTERM, signal.SIGINT) as signals:
        listener = await create_tcp_listener(local_port=listen_port)

        # Sessions run in their own task group so that they can outlive the
        # accept loop and finish while we drain.
        async with create_task_group() as sessions:
            async with create_task_group() as acceptor:
                acceptor.start_soon(listener.serve, handle, sessions)

                async for signum in signals:
                    logger.info("Received %(signal)s, draining sessions for up to %(drain)ss", {
                        "signal": signum.name,
                        "drain": drain_seconds,
                    })
                    break

                acceptor.cancel_scope.cancel()

            await listener.aclose()
            sessions.cancel_scope.deadline = current_time() + drain_seconds

    close_db_pools()
    logger.info("Shutdown complete")

if __name__ == "__main__":
    run(main)
