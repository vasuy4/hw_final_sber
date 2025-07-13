FROM python:3.11.9-slim-bookworm

WORKDIR .

COPY main.py .

RUN pip install --no-cache-dir flask gunicorn

# EXPOSE 8080

# ENTRYPOINT ["python", "main.py"]
CMD ["gunicorn", "main:app", "-b", "127.0.0.1:8080", "--timeout", "120"]
# docker build -t final_sber .
# docker run -d -p 8080:8080 --name my-app final_sber