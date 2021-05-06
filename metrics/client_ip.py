# stdlib
from typing import Optional
# libs
from ipware import get_client_ip
from geolite2 import geolite2
from cloudcix_metrics import Metric
import atexit
# local
from system_conf.urls_local import urlpatterns

# Set the URLS
urls = urlpatterns[0].url_patterns

reader = geolite2.reader()

atexit.register(lambda: reader.close())


def post_client_ip(**kwargs) -> Optional[Metric]:
    """
    Gets the clients IP from the request, gets more details from the IP
    and sends it to influx
    """
    match = ''
    for p in urls:
        if p.pattern.match(kwargs['request'].get_full_path().lstrip('/')):
            match = p.name
    if match == '':
        return None

    ip = get_client_ip(kwargs['request'])
    ip_match = reader.get(ip[0])
    if ip_match is None:
        return None

    tags = {
        'coords': f'{ip_match["location"]["latitude"]},{ip_match["location"]["longitude"]}',
        'location': ip_match['country']['iso_code'],
        'path': match,
        'method': kwargs['request'].method,
        'status_code': kwargs['response'].status_code,
    }

    return Metric('client_ip', ip, tags)
