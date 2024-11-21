FROM python:3.11-slim-bookworm
WORKDIR /app
RUN apt-get update -y && apt-get install -y avahi-utils
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt
COPY tv.py .
ENTRYPOINT [ "python", "/app/tv.py" ]
