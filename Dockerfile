# Etapa 1: compila o site Flutter
FROM ghcr.io/cirruslabs/flutter:3.35.4 AS web
WORKDIR /src
COPY web/pubspec.yaml web/pubspec.lock ./
RUN flutter pub get
COPY web/ ./
RUN flutter build web --release

# Etapa 2: backend Python que serve a API e o site
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=web /src/build/web ./static
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
