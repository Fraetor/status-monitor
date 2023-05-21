#! /usr/bin/env python3
import asyncio
import dbm
import datetime
from http.client import responses
import requests
import send_email

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def check_get(http_endpoint: str) -> bool:
    try:
        r = requests.get(http_endpoint)
    except ConnectionError:
        return False
    return r.status_code == requests.codes.ok


async def http_check(http_endpoint) -> tuple[str, str]:
    if check_get(http_endpoint):
        status = "UP"
    else:
        # Recheck after 120 seconds to ensure not a false positive.
        asyncio.sleep(120)
        if check_get(http_endpoint):
            status = "UP"
        else:
            status = "DOWN"
    return status


async def test_service(db, config, service_name):
    services = config["services"]
    service = services[service_name]
    status = await http_check(service["http_endpoint"])
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


async def main():
    with open("config.toml", "rb") as fp:
        config = tomllib.load(fp)
    # Unix key-value database thing. Interface is dictionary like, but it only
    # stores bytes.
    with dbm.open("status.dbm", "c") as db:
        async_funcs = (test_service(db, config, sn) for sn in config["services"])
        await asyncio.gather(*async_funcs)


if __name__ == "__main__":
    asyncio.run(main())
