FROM python:3.11-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app
COPY ./docs /code/docs

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8086", "--proxy-headers", "--forwarded-allow-ips", "*"]
