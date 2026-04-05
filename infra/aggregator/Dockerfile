FROM python:3.10-slim

WORKDIR /app

# copy aggregator
COPY aggregator/ ./aggregator

# copy ml module
COPY ml/ ./ml

# install deps
RUN pip install --no-cache-dir \
    prometheus-client \
    requests \
    numpy \
    scikit-learn

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

WORKDIR /app/aggregator

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]