FROM python:3.10-slim

# System libs needed by OpenCV (even headless sometimes pulls deps) + general runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps
COPY apps/api/requirements.txt /app/requirements.txt

# IMPORTANT: ensure we don't accidentally keep old opencv wheels
RUN pip install --no-cache-dir -r /app/requirements.txt && \
    pip uninstall -y opencv-python opencv-contrib-python || true

# Copy code
COPY apps/api /app

# IMPORTANT: allow BOTH styles:
# - app.* (because your main is src/app/main.py)
# - src.app.* (because some files import from src.app...)
ENV PYTHONPATH="/app:/app/src"
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --log-level debug"]
