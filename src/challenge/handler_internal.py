import logging
from typing import Optional, Iterable

import psycopg

from src.db import get_db_connection

from .typing import Action


logger = logging.getLogger(__name__)


class HandlerInternal:
    def __init__(self, services) -> None:
        self._services = services
        self._connection = services["db"] if "db" in services else None
        if self._connection:
            logger.debug("Using existing db from services")

    def _get_connection(self) -> psycopg.Connection:
        if not self._connection:
            logger.debug("Using existing db")
            self._connection = get_db_connection(self._services["app_config"]["db"], "db")

        return self._connection

    def get_action(self, email: str) -> Optional[Action]:
        """
        Return any action for the given challenge email
        """
        with self._get_connection().cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    action_to_take
                    FROM challenges
                    WHERE challenge=%(challenge)s AND challenge_type='E'
                """,
                {"challenge": email}
            )

            result = cursor.fetchone()

            if result:
                return result[0]

        return None

    def get_patterns(self) -> Iterable[tuple[str, str]]:
        """
        Returns any pattern-type actions
        """
        with self._get_connection().cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    challenge, action_to_take
                    FROM challenges
                    WHERE challenge_type='P'
                """
            )

            results = cursor.fetchall()

            cursor.close()

            return results
