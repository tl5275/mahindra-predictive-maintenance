FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_INDEX_URL=https://pypi.org/simple

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --timeout 100 -r requirements.txt PyYAML==6.0.2 httpx==0.28.1

COPY backend /app/backend
COPY simulator /app/simulator
COPY config /app/config

CMD ["python", "-m", "simulator.fleet_simulator", "--sleep", "0.2", "--batch-size", "100"]
