import json
from typing import Iterable, Optional, Tuple

from config import Config
import psycopg

from .typing import Action

from src import services


class HandlerDb:
    def __init__(self, app_config: Config = None) -> None:
        self.connection = services["db"] if "db" in services else None
        self.app_config = app_config if app_config else services["app_config"]

    def _get_connection(self) -> psycopg.Connection:
        """
        Return the database connection.
        """
        if not self.connection:
            try:
                self.connection = psycopg.connect(
                    dbname=self.app_config.get("db.name", "postconfirm"),
                    user=self.app_config.get("db.user", "postconfirm"),
                    password=self.app_config.get("db.password", None),
                    host=self.app_config.get("db.host", "localhost"),
                    port=self.app_config.get("db.port", 5432)
                )
            except psycopg.OperationalError as e:
                print(f"The error '{e}' occurred")
                raise e

        return self.connection

    def get_action_for_sender(self, sender: str) -> Optional[Tuple[Action, str]]:
        """
        Return any action for the given sender
        """
        with self._get_connection().cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    action, ref
                    FROM senders
                    WHERE sender=%(sender)s AND type='E'
                UNION
                SELECT
                    action, ref
                    FROM senders_static
                    WHERE sender=%(sender)s AND type='E'
                """,
                {"sender": sender}
            )
            result = cursor.fetchone()

            if result:
                return result

        return ('unknown', None)

    def get_patterns(self) -> Iterable[Tuple[str, str, str]]:
        """
        Returns any pattern-type actions
        """
        with self._get_connection().cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    sender, action, ref
                    FROM senders
                    WHERE type='P'
                UNION
                SELECT
                    sender, action, ref
                    FROM senders_static
                    WHERE type='P'
                """
            )

            yield cursor

    def set_action_for_sender(self, sender: str, action: Action, ref: str) -> bool:
        """
        Sets the action for the sender
        """
        connection = self._get_connection()
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO senders
                        (sender, action, ref, type, source)
                        VALUES
                            (%(sender)s, %(action)s, %(ref)s, 'E', 'postconfirm')
                        ON CONFLICT (sender)
                            DO UPDATE SET action=%(action)s
                    """,
                    {"sender": sender, "action": action, "ref": ref}
                )
                connection.commit()
                return True

            except Exception as e:
                print(f"ERROR setting sender: {e}", flush=True)
                return False

    def stash_message_for_sender(
        self, sender: str, msg: str, recipients: list[str]
    ) -> bool:
        """
        Stores the message for the sender
        """
        connection = self._get_connection()
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO stash
                        (sender, recipients, message)
                        VALUES
                            (%(sender)s, %(recipients)s, %(message)s)
                    """,
                    {"sender": sender, "recipients": json.dumps(recipients), "message": msg}
                )
                connection.commit()
                return True

            except Exception as e:
                print(f"ERROR stashing mail: {e}")
                return False

    def unstash_messages_for_sender(
        self, sender: str
    ) -> Iterable[Tuple[str, list[str]]]:
        """
        Yields the messages for the sender
        """
        connection = self._get_connection()

        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    SELECT
                        id, recipients, message
                        FROM stash
                        WHERE sender=%(sender)s
                    """,
                    {"sender": sender}
                )

                for (row_id, recipients, message) in cursor:
                    yield (json.loads(recipients), message)

                    # Use a different cursor to avoid clobbering the in-progress loop
                    connection.cursor().execute(
                        """
                        DELETE FROM stash
                            WHERE id=%(row_id)s
                        """,
                        {"row_id": row_id}
                    )
                    connection.commit()

                cursor.execute(
                    """
                    SELECT
                        id, recipients, message
                        FROM stash_static
                        WHERE sender=%(sender)s
                    """,
                    {"sender": sender}
                )

                for (row_id, recipients, message) in cursor:
                    yield (json.loads(recipients), message)

                    # Use a different cursor to avoid clobbering the in-progress loop
                    connection.cursor().execute(
                        """
                        DELETE FROM stash_static
                            WHERE id=%(row_id)s
                        """,
                        {"row_id": row_id}
                    )
                    connection.commit()

            except Exception as e:
                print(f"ERROR unstashing mails: {e}", flush=True)
                return
