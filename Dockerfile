FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

RUN chmod +x run.sh

CMD ["./run.sh"]