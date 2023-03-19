#! /usr/bin/env python3
import smtplib
import ssl
from email.message import EmailMessage
import tomllib


with open("config.toml", "rb") as fp:
    config = tomllib.load(fp)["email"]

# Secure TLS settings.
tls_context = ssl.create_default_context()


def send_email(to: str | list[str], subject: str, body: str) -> None:
    # Allow for an address not in a list.
    if type(to) == str:
        to = [to]
    with smtplib.SMTP_SSL(config["smtp_address"], 465, context=tls_context) as server:
        server.login(config["smtp_username"], config["smtp_password"])
        for to_address in to:
            message = EmailMessage()
            message["From"] = config["from_address"]
            message["To"] = to_address
            message["Subject"] = subject
            message.set_content(body)
            server.send_message(message, config["from_address"], to_address)


if __name__ == "__main__":
    to_address = input("Who do you want to email: ")
    send_email(to_address, "Test Email", "This is a test email sent from python.")
