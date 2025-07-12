FROM python:3.10-slim

# Install necessary utilities
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libreoffice \
    file \
    && pip install --no-cache-dir flask python-magic

WORKDIR /app
COPY . .

CMD ["python", "viewer.py"]
