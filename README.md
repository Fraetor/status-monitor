# Monitoring service

This is a program to monitor HTTP services and send notification emails when
their status changes. It is intended to easily integrate with
[Statuspage](https://statuspage.io), but is hopefully generally useful
otherwise.

## Requirements

- [Python](https://www.python.org) 3.11 or newer.
- [Requests](https://requests.readthedocs.io/)
- An SMTP server to send with. I use [Amazon SES](https://aws.amazon.com/ses/).

## Usage

You must first make a copy of `config.toml.example`, with the `.example` suffix
removed, and change the contained configuration for your services.

Once that is done you can run the tool with `python3 monitor.py`.

Once you have confirmed it as working you will need to regularly run it to
monitor your services. I would suggest putting an entry in your crontab to run
it every 5 minutes. For example:

```sh
# Example crontab entry to run every 5 minutes.
*/5 * * * * /path/to/monitor.py /path/to/config.toml
```
