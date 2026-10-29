FROM ubuntu:26.04@sha256:da6fc2be547864451aa253836dd926da33623312df4a9a243e35dc877c378a78
RUN apt-get update -y && apt-get install -y wget unzip python3
WORKDIR /app/
COPY . .
ENTRYPOINT ["./entrypoint.sh"]
