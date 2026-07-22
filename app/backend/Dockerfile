FROM python:3.12.13-slim-bookworm@sha256:d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b

LABEL org.opencontainers.image.base.name="docker.io/library/python:3.12.13-slim-bookworm" \
    io.eamos.runtime-inventory.schema="runtime_component_inventory.v1" \
    io.eamos.hmmer.version="3.3.2+dfsg-1"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/eamos \
    RUNTIME_BUILD_INVENTORY_PATH=/app/runtime-component-inventory.json

RUN apt-get update \
    && apt-get install -y --no-install-recommends hmmer=3.3.2+dfsg-1 \
    && rm -rf /var/lib/apt/lists/*

ENV PROTEIN_ANNOTATION_HMMSCAN_PATH=/usr/bin/hmmscan \
    PROTEIN_ANNOTATION_HMMPRESS_PATH=/usr/bin/hmmpress

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python -m app.capabilities.build_inventory \
    --output /app/runtime-component-inventory.json
RUN mkdir -p /home/eamos /app/data/uploads /app/data/final_reports \
    && chown -R 1000:1000 /home/eamos /app/data

USER 1000:1000

EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
