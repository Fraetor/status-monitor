#! /usr/bin/env python3
import dbm
import datetime
import tomllib
from http.client import responses
import requests
import send_email

with open("config.toml", "rb") as fp:
    config = tomllib.load(fp)

# Unix key-value database thing. Interface is dictionary like, but it only
# stores bytes.
with dbm.open("status.dbm", "c") as db:
    services = config["services"]
    for service_name in services:
        service = services[service_name]
        r = requests.get(service["http_endpoint"])
        if r.status_code == requests.codes.ok:
            status = "UP"
        else:
            status = "DOWN"
        try:
            old_status = db[service_name].decode()
        except KeyError:
            old_status = None
        if status != old_status:
            # Status has changed. Update stored value and send notification email.
            subject = f"{service_name} is {status}"
            timestamp = (
                datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
            )
            body = f"""This is an automated monitoring email.

At {timestamp} the status of {service_name} changed to {status}.
It returned a HTTP status code of {r.status_code} {responses[r.status_code]}.
"""
            send_email.send_email(service["email"], subject, body)
            send_email.send_email(config["to_addresses"], subject, body)
            db[service_name] = status
