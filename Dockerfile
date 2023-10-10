FROM python:3.9-slim
WORKDIR /usr/src/app
COPY Pipfile Pipfile.lock /usr/src/app/
RUN pip install pipenv && pipenv install --system

COPY . .