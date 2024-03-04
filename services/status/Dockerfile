# Use the official Python image as the base image
FROM python:3.11.3-slim-buster

# Set the working directory inside the container
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
RUN apt-get update && apt-get install -y netcat

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r ./requirements.txt

# Copy your Python application code into the container's working directory
COPY . /usr/src/app

# Specify the command to run when the container starts
ENTRYPOINT ["/usr/src/app/status/entrypoint.sh"]