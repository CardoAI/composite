FROM ubuntu:20.04@sha256:8feb4d8ca5354def3d8fce243717141ce31e2c428701f6682bd2fafe15388214
RUN apt-get update -y && apt-get install -y wget unzip python3
WORKDIR /app/
COPY . .
ENTRYPOINT ["./entrypoint.sh"]
