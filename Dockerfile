FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app
ENV AISTUDIO_HOST=0.0.0.0
ENV AISTUDIO_PORT=8123
ENV AISTUDIO_DATA=/app/data
EXPOSE 8123
CMD ["python", "-m", "product"]
