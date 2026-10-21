FROM ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
RUN apt-get update -y && apt-get install -y wget unzip python3
WORKDIR /app/
COPY . .
ENTRYPOINT ["./entrypoint.sh"]
