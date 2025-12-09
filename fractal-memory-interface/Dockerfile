# Multi-stage build для React приложения
# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Копируем package files
COPY package.json ./

# Устанавливаем зависимости (используем install, так как может не быть package-lock.json)
RUN npm install

# Копируем исходный код
COPY . .

# Собираем приложение
RUN npm run build

# Stage 2: Production (Nginx)
FROM nginx:alpine

# Копируем собранное приложение
COPY --from=builder /app/dist /usr/share/nginx/html

# Копируем конфигурацию Nginx (опционально, для SPA routing)
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

