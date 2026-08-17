FROM python:3.12-slim

WORKDIR /app

# libgl1 and libglib2.0-0 are required by PyMuPDF (fitz) for rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
# MALLOC_ARENA_MAX limits glibc's memory pool fragmentation — good practice on all tiers.
ENV MALLOC_ARENA_MAX=2
# TORCHDYNAMO_DISABLE is no longer needed — PyTorch has been removed from this stack.

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]