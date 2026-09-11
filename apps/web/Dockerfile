FROM node:20-slim AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:20-slim
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY package.json vite.config.ts ./
RUN npm install --omit=dev && npm i -g vite@5
EXPOSE 4173
CMD ["vite", "preview", "--host", "0.0.0.0", "--port", "4173"]
