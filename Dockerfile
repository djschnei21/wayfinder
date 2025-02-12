FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY templates/ templates/
COPY logos/ logos/

# Create non-root user for security
RUN useradd -m wayfinder && \
    chown -R wayfinder:wayfinder /app
USER wayfinder

# Configure Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
EXPOSE 5000

# Run with proper host binding for containers
CMD ["flask", "run", "--host=0.0.0.0"]
