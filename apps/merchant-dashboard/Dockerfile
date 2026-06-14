FROM node:20-alpine AS build

WORKDIR /workspace

COPY package.json package-lock.json ./
COPY apps/ops-dashboard/package.json apps/ops-dashboard/package.json
COPY apps/merchant-dashboard/package.json apps/merchant-dashboard/package.json

RUN npm ci

COPY apps/merchant-dashboard apps/merchant-dashboard

RUN npm run merchant-dashboard:build


FROM nginx:1.27-alpine

COPY apps/merchant-dashboard/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/apps/merchant-dashboard/dist /usr/share/nginx/html

EXPOSE 8080
