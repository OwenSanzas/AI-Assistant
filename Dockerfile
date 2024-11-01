# 使用 Ubuntu 作为基础镜像
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

ENV PORT=8000

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN curl https://ollama.ai/install.sh | sh

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

RUN ollama serve & \
    sleep 5 && \
    ollama pull llama3.1:8b && \
    pkill ollama

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]