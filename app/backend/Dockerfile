FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends hmmer \
    && rm -rf /var/lib/apt/lists/*

ENV PROTEIN_ANNOTATION_HMMSCAN_PATH=/usr/bin/hmmscan \
    PROTEIN_ANNOTATION_HMMPRESS_PATH=/usr/bin/hmmpress

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data/uploads

EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
