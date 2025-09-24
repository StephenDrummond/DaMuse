import re

def is_valid_url(url):
    url_regex = r"^https?://"
    return re.match(url_regex, url) is not None