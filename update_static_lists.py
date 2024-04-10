import argparse
import logging
from os.path import basename
import re

import config
import psycopg


logger = logging.getLogger(__name__)


dry_run = False


def add_email_list_entries(cursor, list_name: str, action: str, source_name: str) -> None:
    try:
        with open(list_name, "r") as f:
            for entry in f:
                add_list_entry(cursor, entry.strip(), action, source_name)
    except (FileNotFoundError, PermissionError) as e:
        logger.warning("Skipping invalid email list %(filename)s (%(source)s): %(reason)s", {
            "source": source_name,
            "filename": list_name,
            "reason": str(e)
        })

def add_pattern_list_entries(cursor, list_name: str, action: str, source_name: str) -> None:
    try:
        with open(list_name, "r") as f:
            line_counter = 0
            for entry in f:
                line_counter += 1

                try:
                    stripped_entry = entry.strip()
                    re.compile(stripped_entry)

                    add_list_entry(cursor, stripped_entry, action, source_name, "P")
                except re.error as e:
                    logger.warning("Skipping invalid entry on %(line_counter)d of %(filename)s (%(source)s): %(entry)s -- %(reason)s", {
                                        "line_counter": line_counter,
                                        "filename": list_name,
                                        "source": source_name,
                                        "entry": stripped_entry,
                                        "reason": e.msg
                                    })
    except (FileNotFoundError, PermissionError) as e:
        logger.error("Skipping invalid pattern list %(filename)s (%(source)s): %(reason)s", {
            "source": source_name,
            "filename": list_name,
            "reason": str(e)
        })

def add_list_entry(cursor, sender: str, action: str, source_name: str, sender_type: str = "E", reference: str = None) -> None:
    values = {
        "sender": sender,
        "action": action,
        "source_name": source_name,
        "type": sender_type,
        "reference": reference,
    }

    logger.debug("Adding %(type)s entry for %(sender)s from %(source_name)s as %(action)s with %(reference)s", values)

    if not dry_run:
        cursor.execute(
            """
            INSERT INTO senders_static
                (sender, action, source, ref, type)
                VALUES
                    (%(sender)s, %(action)s, %(source_name)s, %(reference)s, %(type)s)
                ON CONFLICT (sender)
                    DO UPDATE SET action=%(action)s, source=%(source_name)s, ref=%(reference)s, type=%(type)s
            """,
            values
        )


def main():
    global dry_run

    parser = argparse.ArgumentParser(
        prog="update_static_lists",
        description="Admin script to convert the file-based lists into the database"
    )
    parser.add_argument("-c", "--config-file", default="/etc/postconfirm.cfg", type=argparse.FileType())
    parser.add_argument("-n", "--dry-run", action='store_true', help="Do not actually modify the data")

    args = parser.parse_args()

    # Load the configuration
    app_config = config.Config(args.config_file)

    # Set up the root logger
    logging.basicConfig(level=app_config.get('log.level', logging.WARNING))

    # We need to create a connection and start a transaction
    connect_args = {
        "dbname": app_config.get("db.name", "postconfirm"),
        "user": app_config.get("db.user", "postconfirm"),
        "password": app_config.get("db.password", None),
        "host": app_config.get("db.host", "localhost"),
        "port": app_config.get("db.port", 5432)
    }

    dry_run = args.dry_run

    with psycopg.connect(**connect_args) as connection:
        with connection.cursor() as cursor:

            logger.debug("Clearing down old data")

            # Then delete the static data
            if not dry_run:
                cursor.execute(
                    """
                    TRUNCATE
                        senders_static
                    RESTART IDENTITY
                    """
                ) 

            # Then add the new data

            logger.debug("Adding new data")

            email_lists = [
                ("confirmlist", "accept"),
                ("allowlists", "accept"),
                ("whitelists", "accept"),
                ("rejectlists", "reject"),
                ("blacklists", "reject"),
                ("discardlists", "discard"),
            ]

            for config_name, action in email_lists:
                config_lists = app_config.get(config_name, [])

                if isinstance(config_lists, str):
                    config_lists = [config_lists]

                for list_name in config_lists:
                    logger.info("Processing list (type: %(type)s; file: %(file_name)s)", {
                        "type": action,
                        "file_name": list_name
                    })
                    source_name = basename(list_name)

                    add_email_list_entries(cursor, list_name, action, source_name)

            regex_lists = [
                ("allowregex", "accept"),
                ("whiteregex", "accept"),
                ("rejectregex", "reject"),
                ("blackregex", "reject"),
                ("discardregex", "discard"),
            ]

            for config_name, action in regex_lists:
                for list_name in app_config.get(config_name, []):
                    logger.info("Processing regex list (type: %(type)s; file: %(file_name)s)", {
                        "type": action,
                        "file_name": list_name
                    })

                    source_name = basename(list_name)

                    add_pattern_list_entries(cursor, list_name, action, source_name)

            connection.commit()


if __name__ == "__main__":
    main()
