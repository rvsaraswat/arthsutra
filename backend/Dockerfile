# Dockerfile for the FastAPI backend
# --------------------------------------------
# 1️⃣  Base image – slim Python 3.11
# --------------------------------------------

# Use official Python image
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source only
COPY . .

# Expose port
EXPOSE 5174

# Start FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5174"]