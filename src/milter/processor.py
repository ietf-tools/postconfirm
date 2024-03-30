import re
from typing import Union

from kilter.protocol import Accept, Discard, Reject
from kilter.service import Runner, Session

from src.sender import Sender, get_sender

LINE_SEP = "\n"


def recipient_requires_challenge(recipients: list) -> bool:
    # FIXME: Implement recipient_requires_challenge
    return True

def subject_is_challenge_response(subject: str) -> bool:
    reference = get_challenge_reference_from_subject(subject)

    return True if reference else False

def form_header(header) -> str:
    return f"{header.name}:{header.value.tobytes().decode()}"

def reform_email_text(headers: list, body_chunks: list) -> str:
    return f"{LINE_SEP.join(form_header(header for header in headers))}{LINE_SEP}{LINE_SEP}{''.join(body_chunks)}"

def send_challenge(sender: Sender, reference: str) -> None:
    """
    Send the challenge email to the sender, with the reference
    and then update the sender to indicate this.
    """
    pass

def get_challenge_reference_from_subject(subject: str) -> str:
    """
    Extracts the challenge reference from the subject
    """
    match = re.match(r"challenge: ([a-f0-9]+)", subject, re.IGNORECASE)
    return match[1] if match else None

@Runner
async def handle(session: Session) -> Union[Accept, Reject, Discard]:
    """
    The milter processor for postconfirm.

    Decisions are made on the basis of where the message is going to and
    then who the sender is, since not all messages will be covered by the
    challenge system. Once we know that at least one destination requires
    the challenge the sender is examined. In the simple cases the action
    will be either "accept", "reject", or "discard" and the appropriate
    response can be sent immediately.

    If the sender is "unknown" then we start the challenge process, which
    includes stashing the mail and indicating that the original should be
    discarded. The sender will be marked as "confirm" and the challenge
    sent. If the sender is "confirm" then we do not need to resend the
    challenge and proceed with just stashing the mail and discarding the
    original.

    The other case is that this is a challenge response. If the sender is
    "confirm" and the response is correct then the stashed mails are
    resent. The challenge response is then discarded. If the challenge
    response fails then the mail is rejected. If the sender is in any
    other state then the response is simply discarded.
    """

    # First we set up our Sender
    mail_from = await session.envelope_from()
    sender = get_sender(mail_from)

    # Then we can gather the recipients. The order is determined by the
    # SMTP protocol.
    mail_recipients = [
        recipient async for recipient in session.envelope_recipients()
    ]

    requires_challenge = recipient_requires_challenge(mail_recipients)

    # In order to tell if this is a challenge response we need the
    # subject, which means collecting all the headers.

    mail_headers = []
    mail_subject = None

    async with session.headers as headers:
        async for header in headers:
            if header.name == "Subject":
                mail_subject = header.value.tobytes().decode()

            mail_headers.append(header)

    is_challenge_response = subject_is_challenge_response(mail_subject)

    # Now we can determine the course of action
    if requires_challenge and not is_challenge_response:
        # Process the sender
        action = sender.get_action()

        if action == "accept":
            return Accept()
        elif action == "reject":
            return Reject()
        elif action == "discard":
            return Discard()

        # The remaining options are "unknown" or "confirm". In both cases
        # we need to stash the mail. That means completing the collection.
        mail_body = []
        async with session.body as body:
            async for chunk in body:
                mail_body.append(chunk.tobytes().decode())

        mail_as_text = reform_email_text(mail_headers, mail_body)

        challenge_reference = sender.stash_email(mail_as_text, mail_recipients)

        if action == "unknown":
            send_challenge(sender, challenge_reference)

        return Discard()

    elif is_challenge_response:
        # Process the response
        action = sender.get_action()

        if action == "confirm":
            reference = get_challenge_reference_from_subject(mail_subject)

            if not sender.validate_ref(reference):
                # Reject the message
                return Reject()

            # Valid, so release the messages
            with services["remailer"] as mailer:
                for (recipients, message) in sender.unstash_emails():
                    mailer.sendmail(sender.get_email(), recipients, message)

    # Anything else is just accepted
    return Accept()
