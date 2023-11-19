FROM cgr.dev/chainguard/wolfi-base
ARG version=3.11
WORKDIR /app
RUN apk add avahi python-$version py${version}-pip\
 && chown -R nonroot.nonroot /app/
COPY requirements.txt /app/
RUN  pip3 install -r requirements.txt
COPY tv.py .
ENTRYPOINT [ "python", "/app/tv.py" ]
