FROM python:3.10
WORKDIR /application_framework
COPY . .

# Ensure your package index is up-to-date
RUN apt update && apt upgrade -y

# Install libs necessary for all applications
RUN pip3 install -U pip && pip3 install -r requirements.txt
