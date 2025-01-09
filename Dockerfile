FROM python:3.7
WORKDIR /application_framework
COPY . .
# Update pip
RUN pip3 install -U pip
# Install libs necessary for all applications
RUN pip3 install -r requirements.txt
