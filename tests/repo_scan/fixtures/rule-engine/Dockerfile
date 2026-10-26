FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0"]
