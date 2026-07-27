# Stage 1: Builder — compila el SPA con Vite (misma major que CI, ver ci.yml)
FROM node:24-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vacío a propósito: en producción el frontend y el backend se sirven en el
# mismo origen (nginx reenvía /api/* a "app"), así que las llamadas relativas
# no necesitan conocer un host público en tiempo de build.
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build


# Stage 2: Runtime — nginx sirviendo los estáticos + proxy same-origin del API
FROM nginx:1.27-alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/healthz || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
