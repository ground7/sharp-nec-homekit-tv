FROM python:3.11-alpine
WORKDIR /app
RUN apk add avahi libcec-dev gcc make
COPY requirements.txt /app/
RUN  pip3 install --no-cache-dir -r requirements.txt
COPY tv.py .
ENTRYPOINT [ "python", "/app/tv.py" ]
