import logging

from aiosmtplib import SMTP
from config import Config

logger = logging.getLogger(__name__)


class Remailer:
    """
    Provides a simple wrapper around the python mail code that is context
    aware, allows for re-use and will default the envelope sender.

    Configuration is via the following keys:
    * `smtp_host` (defaults to "localhost") as the host to send via
    * `smtp_port` (defaults to 25) as the port to connect to on the `smtp_host`
    * `smtp_validate_certs` (defaults to False) boolean as to whether to
    validate the certificate presented by the smtp server
    * `remailer_sender` (defaults to "<>") as the default envelope sender
    * `smtp_username` (optional) username for SASL PLAIN authentication
    * `smtp_password` (optional) password for SASL PLAIN authentication

    When `smtp_username` and `smtp_password` are both set, the connection
    will negotiate STARTTLS before authenticating. Both must be set or both
    must be unset.
    """

    def __init__(self, app_config: Config):
        self.host = app_config.get("smtp_host", "localhost")
        self.port = app_config.get("smtp_port", 25)
        self.helo_host = app_config.get("smtp_helo_host", "localhost")
        if app_config.get("smtp_validate_certs", "False").lower() in [
            "true",
            "1",
            "t",
            "y",
            "yes",
        ]:
            self.validate_certs = True
        else:
            self.validate_certs = False
        self.sender_from = app_config.get("remail_sender", "<>")

        self.username = app_config.get("smtp_username", None)
        self.password = app_config.get("smtp_password", None)

        if bool(self.username) != bool(self.password):
            raise ValueError(
                "smtp_username and smtp_password must both be set or both be unset"
            )

    async def sendmail(
        self, recipients: list[str], message: str, sender: str = None
    ) -> any:
        if sender is None:
            sender = self.sender_from
        try:
            async with SMTP(
                hostname=self.host,
                port=self.port,
                local_hostname=self.helo_host,
                validate_certs=self.validate_certs
            ) as smtp:
                if self.username:
                    await smtp.login(self.username, self.password)
                return await smtp.sendmail(sender, recipients, message.encode("UTF-8"))
        except Exception as e:
            logger.error("Exception in SMTP: %(reason)s", {"reason": str(e)})
            return False
