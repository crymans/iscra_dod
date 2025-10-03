FROM python:3.12-slim

WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     && rm -rf /var/lib/apt/lists/*

# RUN mkdir -p /app/data && chmod 755 /app/data

COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

COPY . .

CMD ["python", "-m", "bot.main"]