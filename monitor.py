#! /usr/bin/env python3

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage
import argparse
import datetime
import dbm
import itertools
import smtplib
import ssl
import sys
import time
import tomllib

import requests

# Secure TLS settings.
tls_context = ssl.create_default_context()


def iter_maybe(thing) -> Iterable:
    """Ensure thing is Iterable. Strings count as atoms."""
    if isinstance(thing, Iterable) and not isinstance(thing, str):
        return thing
    return (thing,)


class Emailer:
    """Send emails from a specific address and mail server.

    Parameters
    ----------
    to_addresses: str | list[str]
        Email address(es) to send to in addition to the per-service email.
    from_address: str
        Email address to send from.
    smtp_address: str
        Address of the SMTP server to use.
    smtp_username: str
        Username to login to the SMTP server with.
    smtp_password: str
        Password to login to the SMTP server with.
    """

    def __init__(
        self,
        to_addresses: str | list[str],
        from_address: str,
        smtp_address: str,
        smtp_username: str,
        smtp_password: str,
    ) -> None:
        self.to_addresses = to_addresses
        self.from_address = from_address
        self.smtp_address = smtp_address
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password

    def send_email(self, to: str | list[str], subject: str, body: str) -> None:
        """Send an email.

        The email is sent as ``text/plain``.

        Parameters
        ----------
        to: str | list[str]
            Email address(es) to send to.
        subject: str
            Email subject.
        body:
            Email body.
        """
        # Minimal set of addresses to send to.
        to = set(itertools.chain(iter_maybe(self.to_addresses), iter_maybe(to)))
        # Construct email message.
        message = EmailMessage()
        message["From"] = self.from_address
        message["Subject"] = subject
        message.set_content(body)
        # Login to server and send emails to each address.
        with smtplib.SMTP_SSL(self.smtp_address, 465, context=tls_context) as server:
            server.login(self.smtp_username, self.smtp_password)
            for to_address in to:
                del message["To"]
                message["To"] = to_address
                server.send_message(message, self.from_address, to_address)


def check_get(http_endpoint: str) -> bool:
    """Check a HTTP GET request to a given URL succeeds."""
    headers = {"User-Agent": "status-monitor/1.0 (https://www.frost.cx/)"}
    try:
        r = requests.get(http_endpoint, timeout=30, headers=headers)
    except ConnectionError:
        return False
    return r.status_code == requests.codes.ok


def http_check(http_endpoint: str) -> bool:
    """Check an endpoint, retrying a couple times."""
    if not check_get(http_endpoint):
        # Recheck after 15 seconds to ensure not a false positive.
        time.sleep(15)
        if not check_get(http_endpoint):
            # And again 30 seconds after that to be sure.
            time.sleep(30)
            if not check_get(http_endpoint):
                return False
    return True


def test_service(db, emailer: Emailer, name: str, email: str, http_endpoint: str):
    """Test a single service.

    Sends an email and updates the database on a status change.
    """
    status = "UP" if http_check(http_endpoint) else "DOWN"
    try:
        old_status = db[name].decode()
    except (KeyError, UnicodeError):
        old_status = None
    # Only do something if the status has changed.
    if status != old_status:
        # Status has changed. Update stored value and send notification email.
        subject = f"{name} is {status}"
        timestamp = (
            datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat()
        )
        body = f"This is an automated monitoring email.\n\nAt {timestamp} the status of {name} changed to {status}."
        # Email with status updates.
        emailer.send_email(email, subject, body)
        # Update database.
        db[name] = status.encode()


def get_config() -> dict:
    """Get configuration from file given on command line."""
    parser = argparse.ArgumentParser(prog="status-monitor")
    parser.add_argument(
        "config", default="./config.toml", help="path to configuration file"
    )
    parser.add_argument("database", default="./status.dbm", help="path to status database")
    args = parser.parse_args()
    try:
        with open(args.config, "rb") as fp:
            configuration = tomllib.load(fp)
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    return configuration, args.database


def main():
    """Run status monitor once."""
    config, database_path = get_config()
    # dbm is Unix key-value database thing. Interface is dictionary like, but it
    # only stores bytes.
    emailer = Emailer(**config["email"])
    with dbm.open(database_path, "c") as db, ThreadPoolExecutor() as executor:
        for service_name, service in config["services"].items():
            executor.submit(
                test_service,
                db,
                emailer,
                service_name,
                service["email"],
                service["http_endpoint"],
            )


if __name__ == "__main__":
    main()
