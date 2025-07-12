FROM debian:bullseye

RUN apt-get update && \
    apt-get install -y yara python3 python3-pip && \
    pip3 install flask

WORKDIR /app

COPY scan.py .

CMD ["python3", "scan.py"]
