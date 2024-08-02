FROM python:3.10.12

WORKDIR /api_app

COPY ./api_app/requirements.txt .

RUN pip install --no-cache-dir -r ./requirements.txt

COPY /api_app/ .

CMD mkdir -p /tmp/socket && gunicorn -w=1 --bind=unix:/tmp/socket/gunicorn.sock \
 -k uvicorn.workers.UvicornWorker \
 main:app
