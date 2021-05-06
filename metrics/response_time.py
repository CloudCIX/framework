from typing import Optional
# libs
from cloudcix_metrics import Metric
# local
from system_conf.urls_local import urlpatterns

# Set up the URLS
urls = urlpatterns[0].url_patterns


def post_response_time(request, response, **kwargs) -> Optional[Metric]:
    """
    Sends the response time for a request to influx
    """
    path_name = None
    path = request.get_full_path().lstrip('/').split('?')[0]
    # Check the application's urlpatterns, find the one that matches the request path and get the name of that pattern
    for p in urls:
        if p.pattern.match(path):
            path_name = p.name
    if path_name is None:
        return None

    tags = {
        'path': path_name,
        'method': request.method,
        'status_code': response.status_code,
    }
    return Metric('response_time', kwargs['time'], tags)
