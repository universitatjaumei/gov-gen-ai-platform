#!/bin/bash
set -e

echo "Iniciando despliegue de Gov Gen AI Platform..."

required_vars=("DATABASE_URL" "DATABASE_URL_SYNC" "JWT_SECRET_KEY" "GOOGLE_API_KEY" "POSTGRES_USER" "POSTGRES_PASSWORD" "POSTGRES_DB" "MINIO_ROOT_USER" "MINIO_ROOT_PASSWORD")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: Variable $var no está definida"
        exit 1
    fi
done

echo "Variables de entorno verificadas"

echo "Construyendo imagen Docker..."
docker compose -f docker-compose.prod.yml build app

echo "Iniciando base de datos y almacenamiento..."
docker compose -f docker-compose.prod.yml up -d postgres minio

echo "Esperando que postgres esté listo..."
docker compose -f docker-compose.prod.yml run --rm migrate alembic current || true

echo "Ejecutando migraciones..."
docker compose -f docker-compose.prod.yml run --rm migrate

echo "Iniciando servidor..."
docker compose -f docker-compose.prod.yml up -d app

echo "Verificando health del servicio (espera 20s)..."
sleep 20
if curl -sf http://localhost:8000/health | grep -q "healthy"; then
    echo "Despliegue completado exitosamente"
else
    echo "Error: El servicio no está healthy"
    docker compose -f docker-compose.prod.yml logs app
    exit 1
fi
