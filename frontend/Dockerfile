# Stage 1: Builder — compila el SPA con Vite (misma major que CI, ver ci.yml)
FROM node:25-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vacío a propósito: en producción el frontend y el backend se sirven en el
# mismo origen (nginx reenvía /api/* a "app"), así que las llamadas relativas
# no necesitan conocer un host público en tiempo de build.
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}

# El prefijo del panel (DOM.2). El defecto es el de PRODUCCIÓN y no el de
# desarrollo, porque esta imagen ES producción: `deploy.yml` la construye con
# `docker build ./frontend` a secas, sin pasar build-args.
#
# Vite escribe las URL de los recursos en el HTML al compilar, así que este valor
# tiene que coincidir con la ruta bajo la que nginx sirve el `dist` (más abajo) y
# con la que el proxy encamina al frontend (`deploy/vm/Caddyfile`). Son tres
# ficheros y una sola verdad; lo comprueba
# `server/tests/infra/test_dom2_el_panel_bajo_su_prefijo.py`.
ARG VITE_BASE_PATH="/panel/"
ENV VITE_BASE_PATH=${VITE_BASE_PATH}

RUN npm run build


# Stage 2: Runtime — nginx sirviendo los estáticos + proxy same-origin del API
FROM nginx:1.27-alpine AS runtime

# El `dist` va al SUBDIRECTORIO del prefijo, no a la raíz. Así `/panel/assets/x.js`
# es un fichero que existe de verdad y no el `index.html` devuelto por el fallback
# del SPA: cuando eso pasa, el navegador dice «Unexpected token '<'» y nadie mira
# nginx. Y así la imagen se comporta igual abierta directa que detrás del proxy,
# sin depender de que alguien le quite el prefijo por delante.
COPY --from=builder /app/dist /usr/share/nginx/html/panel
COPY nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/healthz || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
