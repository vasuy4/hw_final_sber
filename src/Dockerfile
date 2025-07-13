FROM python:3.11.9-slim

WORKDIR /app

COPY app.py /app/

RUN pip install --no-cache-dir flask

EXPOSE 8080

CMD ["python", "app.py"]