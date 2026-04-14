# Stage 1: Build Tailwind CSS
FROM node:20-slim AS css-builder
WORKDIR /build
COPY package.json tailwind.config.js ./
COPY static/css/input.css static/css/
COPY app/templates/ app/templates/
RUN npm install && npx tailwindcss -i static/css/input.css -o static/css/dist.css --minify

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY . .
COPY --from=css-builder /build/static/css/dist.css static/css/dist.css

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
