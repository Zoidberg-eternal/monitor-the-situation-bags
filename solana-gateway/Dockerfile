FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY tsconfig.json ./
COPY src ./src

RUN npx tsc

EXPOSE 3403

CMD ["node", "dist/index.js"]
