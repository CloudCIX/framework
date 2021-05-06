"""system_conf URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

If publishing docs this file should replace system_conf/urls.py
"""

# lib
from cloudcix_rest.views import DocumentationView
from django.urls import path
# Import the local urls created by the individual applications
from system_conf.urls_local import urlpatterns

# Add on the url for documentation
urlpatterns.append(
    path(
        'documentation/',
        DocumentationView.as_view(),
        name='api_documentation',
    ),
)
