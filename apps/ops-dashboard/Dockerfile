FROM node:20-alpine AS build

WORKDIR /workspace

COPY package.json package-lock.json ./
COPY apps/ops-dashboard/package.json apps/ops-dashboard/package.json

RUN npm ci

COPY apps/ops-dashboard apps/ops-dashboard

RUN npm run ops-dashboard:build


FROM nginx:1.27-alpine

COPY apps/ops-dashboard/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/apps/ops-dashboard/dist /usr/share/nginx/html

EXPOSE 8080
