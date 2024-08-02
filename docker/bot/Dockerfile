FROM python:3.10.12

WORKDIR /bot

COPY ./bot/requirements.txt .

RUN pip install --no-cache-dir -r ./requirements.txt

COPY /bot/ .

CMD python3 /bot/main.py
