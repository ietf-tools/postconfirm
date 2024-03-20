import argparse
import sys

from anyio import create_tcp_listener, run
import config

from src.milter import Processor

async def main():
    parser = argparse.ArgumentParser(
        prog="postconfirm",
        description="Milter handler for confirming that emails come from valid email addresses"
    )
    parser.add_argument("-c", "--config-file", default="/etc/postconfirm.cfg", type=argparse.FileType())
    parser.add_argument("-p", "--port")

    args = parser.parse_args()

    settings = config.Config(args.config_file)

    milter = Processor(settings)

    listen_port = args.port or settings.get("milter_port", 1999)
    listener = await create_tcp_listener(local_port=listen_port)
    await listener.serve(milter.handle)


if __name__ == "__main__":
    run(main)