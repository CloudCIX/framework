# Framework

This is the base Djago Rest Framework for Python3 CloudCIX APIs. It contains functions and settings that are common and available to all CloudCIX APIs. It is extended by 

a) Copying the app repository into the framework e.g. framework/membership
b) Moving the settings_local.py file for the app to framework/system_conf/settings_local.py
c) Moving the urls_local.py file for the app to framework/system_conf/urls_local.py
d) Moving the errors folder file for the app to framework/errors

## Framework Environment Variables

### `POD_SECRET_KEY`
- This is the Django secret key value that is used to secure signed data. 
- More information can be found [here](https://docs.djangoproject.com/en/2.2/topics/signing/#protecting-the-secret-key)

### `POD_NAME`
- The name of the POD. 
- This value is used to determine urls for the CloudCIX API. e.g. membership.{POD_NAME}.{ORGANIZATION_URL}


### `ORGANIZATION_URL`
- The Organization URL of the POD e.g. cloudcix.com 
- This value is used to determine urls for the CloudCIX API. e.g. membership.{POD_NAME}.{ORGANIZATION_URL}

### `PAM_NAME` (optional)
- Default is "pam". 
- This value is used to determine urls for the PAM monitioring the COP where the framework is deployed. e.g. {PAM_NAME}.{PAM_ORGANIZATION_URL}

### `PAM_ORGANIZATION_URL` (optional)
- Default is "example.com". This value is used to determine urls for the PAM monitioring the COP where the framework is deployed. e.g. {PAM_NAME}.{PAM_ORGANIZATION_URL}

### `EMAIL_HOST` 
- The host to use for sending email.
- More information can be found [here](https://docs.djangoproject.com/en/2.2/ref/settings/#email-host)

### `EMAIL_HOST_USER` 
- Username to use for the SMTP server defined in `EMAIL_HOST`. 
- More information can be found [here](https://docs.djangoproject.com/en/2.2/ref/settings/#email-host-user)

### `EMAIL_HOST_PASSWORD` 
- Password to use for the SMTP server defined in `EMAIL_HOST`. 
- This setting is used in conjunction with `EMAIL_HOST_USER` when authenticating to the SMTP server.
- More information can be found [here](https://docs.djangoproject.com/en/2.2/ref/settings/#email-host-password)

### `EMAIL_PORT` (optional)
- Default is 25.
- Port to use for the SMTP server defined in `EMAIL_HOST`. 
- More information can be found [here](https://docs.djangoproject.com/en/2.2/ref/settings/#email-port)

### `LOGSTASH_ENABLE` (optional)
- Default is False.

### `LOGSTASH_URL` (optional)
- Default is an empty string ('').

### `INFLUX_URL` (optional)
- Default is an empty string ('').

### `ELASTICSEARCH_DSL` (optional)
- Default is an empty string ('').

## Framework Volumes

### `/application_framework/public-key.rsa`
- Public key is used by all CloudCIX APIs to decode JSON Web tokens (JWT) created by the Membership API.
