FROM python:3.10-slim

WORKDIR /app

# Copy entire infra folder
COPY . .

# Install normal packages FIRST (default PyPI)
RUN pip install --no-cache-dir \
    prometheus-client \
    requests \
    numpy \
    scikit-learn

# Install CPU-only torch separately
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Run aggregator
CMD ["python", "aggregator/main.py"]