
wsgi_app = 'system_conf.wsgi:application'

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# SSL
keyfile = None
certfile = None

# Workers
bind = ['0.0.0.0:443']
workers = 4
timeout = 60
