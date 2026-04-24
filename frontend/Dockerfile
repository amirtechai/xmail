FROM node:20-alpine AS builder

WORKDIR /app

# VITE_ vars are compile-time — pass via --build-arg in production
ARG VITE_API_URL=http://localhost:8000/api
ENV VITE_API_URL=${VITE_API_URL}

COPY package*.json ./
RUN npm ci --frozen-lockfile

COPY . .
RUN npm run build

# Production stage — unprivileged nginx (runs as uid 101, port 8080)
FROM nginxinc/nginx-unprivileged:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

USER nginx

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
