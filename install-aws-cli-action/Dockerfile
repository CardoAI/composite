FROM ubuntu:22.04@sha256:962f6cadeae0ea6284001009daa4cc9a8c37e75d1f5191cf0eb83fe565b63dd7
RUN apt-get update -y && apt-get install -y wget unzip python3
WORKDIR /app/
COPY . .
ENTRYPOINT ["./entrypoint.sh"]
