# Dockerfile for the FastAPI backend
# --------------------------------------------
# 1️⃣  Base image – slim Python 3.11
# --------------------------------------------
FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED 1
WORKDIR /app

# --------------------------------------------
# 2️⃣  Install dependencies
# --------------------------------------------
# If you have a requirements.txt, copy it first.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------------------
# 3️⃣  Copy source code
# --------------------------------------------
COPY . .

# --------------------------------------------
# 4️⃣  Run the FastAPI server
# --------------------------------------------
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "5174"]