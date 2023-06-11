#! /usr/bin/env python3

import dbm
import datetime
import time
import concurrent.futures
import requests
import send_email

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def check_get(http_endpoint: str) -> bool:
    try:
        r = requests.get(http_endpoint, timeout=30)
    except ConnectionError:
        return False
    return r.status_code == requests.codes.ok


def http_check(http_endpoint) -> tuple[str, str]:
    if check_get(http_endpoint):
        status = "UP"
    else:
        # Recheck after 60 seconds to ensure not a false positive.
        time.sleep(60)
        if check_get(http_endpoint):
            status = "UP"
        else:
            status = "DOWN"
    return status


def test_service(db, config, service_name):
    services = config["services"]
    service = services[service_name]
    status = http_check(service["http_endpoint"])
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

At {timestamp} the status of {service_name} changed to {status}."""
        send_email.send_email(service["email"], subject, body)
        send_email.send_email(config["to_addresses"], subject, body)
        db[service_name] = status


def main():
    with open("config.toml", "rb") as fp:
        config = tomllib.load(fp)
    # Unix key-value database thing. Interface is dictionary like, but it only
    # stores bytes.
    with dbm.open("status.dbm", "c") as db:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(test_service, db, config, service)
                for service in config["services"]
            ]
            concurrent.futures.wait(futures, return_when="ALL_COMPLETED")


if __name__ == "__main__":
    main()
