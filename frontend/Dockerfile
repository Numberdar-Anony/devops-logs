FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* .npmrc* ./ 2>/dev/null || true
RUN npm install
COPY . .
EXPOSE 5173
ENV VITE_API_BASE_URL=http://backend:8000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
