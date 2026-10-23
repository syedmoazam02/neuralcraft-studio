# =============================================================================
# NeuralCraft Studio — Dockerfile
# =============================================================================
# Build:   docker build -t neuralcraft-studio .
# Run:     docker run --env-file .env -p 8000:8000 neuralcraft-studio
# =============================================================================

# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── Runtime environment flags ─────────────────────────────────────────────────
# Prevents Python from writing .pyc files inside the container.
ENV PYTHONDONTWRITEBYTECODE=1
# Forces stdout/stderr to be unbuffered so logs appear in real-time.
ENV PYTHONUNBUFFERED=1

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Dependency installation (cached layer) ────────────────────────────────────
# Copy ONLY requirements.txt first so Docker caches this layer and skips
# re-installing packages when only application code changes.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Pre-create the logs directory so the container can write traces ───────────
RUN mkdir -p logs

# ── Port exposure ─────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Default command ───────────────────────────────────────────────────────────
# run.py reads PORT from the environment (default: 8000) and binds to 0.0.0.0.
CMD ["python", "run.py"]
