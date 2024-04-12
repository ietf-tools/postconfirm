import logging
from typing import Optional

import psycopg


logger = logging.getLogger(__name__)


connection_cache = {}


def get_db_connection(config_fragment: dict, cache_key: Optional[str] = None) -> psycopg.Connection:
    global connection_cache

    if not cache_key or cache_key not in connection_cache:
        try:
            connection = psycopg.connect(
                dbname=config_fragment.get("name", "postconfirm"),
                user=config_fragment.get("user", "postconfirm"),
                password=config_fragment.get("password", None),
                host=config_fragment.get("host", "localhost"),
                port=config_fragment.get("port", 5432)
            )
        except psycopg.OperationalError as e:
            print(f"The error '{e}' occurred")
            raise e

        if cache_key:
            connection_cache[cache_key] = connection

        return connection
    else:
        return connection_cache[cache_key]
