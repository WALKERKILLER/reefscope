# 构建阶段
FROM node:22-bookworm-slim AS build

WORKDIR /app

ARG VITE_API_BASE_URL=
ARG VITE_DEFAULT_MODEL_PATH=
ARG VITE_DEFAULT_TARGET_LABELS=fish
ARG VITE_DEFAULT_CONFIDENCE_THRESHOLD=0.25
ARG VITE_DEFAULT_IOU_THRESHOLD=0.45
ARG VITE_DEFAULT_FRAME_STRIDE=5

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_DEFAULT_MODEL_PATH=$VITE_DEFAULT_MODEL_PATH
ENV VITE_DEFAULT_TARGET_LABELS=$VITE_DEFAULT_TARGET_LABELS
ENV VITE_DEFAULT_CONFIDENCE_THRESHOLD=$VITE_DEFAULT_CONFIDENCE_THRESHOLD
ENV VITE_DEFAULT_IOU_THRESHOLD=$VITE_DEFAULT_IOU_THRESHOLD
ENV VITE_DEFAULT_FRAME_STRIDE=$VITE_DEFAULT_FRAME_STRIDE

COPY package*.json ./
RUN npm ci --registry=https://registry.npmjs.org

COPY . .
RUN npm run build

# 运行阶段
FROM nginx:1.27-bookworm

COPY --from=build /app/dist /usr/share/nginx/html

# 自定义 nginx 配置以处理 SPA 路由
RUN echo 'server { \
    listen 18080; \
    server_name _; \
    client_max_body_size 500M; \
    root /usr/share/nginx/html; \
    index index.html; \
    add_header X-Content-Type-Options "nosniff" always; \
    add_header X-Frame-Options "DENY" always; \
    add_header Referrer-Policy "strict-origin-when-cross-origin" always; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    location /api/ { \
        proxy_pass http://backend:8000/api/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
    } \
    location /media/ { \
        proxy_pass http://backend:8000/media/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 18080

CMD ["nginx", "-g", "daemon off;"]
