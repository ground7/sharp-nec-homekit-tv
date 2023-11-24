FROM python:3.11-bookworm-slim
WORKDIR /app
RUN apt-get install avahi libcec-dev build-essential python-dev
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt
COPY tv.py .
ENTRYPOINT [ "python", "/app/tv.py" ]
