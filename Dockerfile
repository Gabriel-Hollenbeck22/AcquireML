# Runs the AcquireML web UI backend (FastAPI) for the hosted demo.
# The frontend is deployed separately (static build on Vercel) and talks
# to this container over HTTP.
FROM python:3.11-slim

# HOME controls where store.py's SESSIONS_DIR (~/.acquireml/sessions) lands.
# Fixing it to /data and mounting a Fly.io volume there means session
# databases survive restarts and redeploys with no code changes.
ENV HOME=/data
RUN mkdir -p /data

WORKDIR /app
COPY pyproject.toml README.md ./
COPY acquireml ./acquireml
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "acquireml.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
