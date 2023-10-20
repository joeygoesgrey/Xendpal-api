FROM python:3.9-slim
WORKDIR /usr/src/app
COPY Pipfile Pipfile.lock /usr/src/app/
RUN pip install pipenv && pipenv install --system

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
