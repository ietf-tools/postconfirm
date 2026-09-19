import argparse
import logging

from anyio import run
import config

from src import services
from src.remailer import Remailer
from src.milter.processor import release_messages
from src.sender import get_sender


async def main():
    parser = argparse.ArgumentParser(
        description="Manually release stashed messages for a sender"
    )
    parser.add_argument("-c", "--config-file", default="/etc/postconfirm.cfg", type=argparse.FileType())
    parser.add_argument("email", help="Sender email address to release messages for")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    app_config = config.Config(args.config_file)
    services["app_config"] = app_config
    services["remailer"] = Remailer(app_config)

    sender = get_sender(args.email)
    await release_messages(sender)


if __name__ == "__main__":
    run(main)
