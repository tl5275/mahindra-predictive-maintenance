FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=200
ENV PIP_INDEX_URL=https://pypi.org/simple

WORKDIR /app

COPY ml/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --timeout 200 --prefer-binary \
    fastapi==0.115.9 \
    uvicorn[standard]==0.34.0 \
    -r requirements.txt

COPY ml /app/ml

EXPOSE 8010

CMD ["python", "ml/anomaly_service.py"]
