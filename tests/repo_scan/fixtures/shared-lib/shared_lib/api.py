import requests


def send_application_context(url, payload):
    return requests.post(url, json=payload, timeout=5)


def health(url):
    return requests.get(url, timeout=5).ok
