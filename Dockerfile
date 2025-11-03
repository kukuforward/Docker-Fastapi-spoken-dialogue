# 1. 基础镜像：用稳定的 Python 3.14 精简版（适配你的依赖，体积小）
FROM python:3.14-slim

# 2. 设置工作目录（避免文件混乱）
WORKDIR /app


# 3. 复制依赖清单（优先复制这个，利用 Docker 缓存：只有 requirements.txt 变了才重新装依赖）
COPY requirements.txt .

# 4. 升级 pip + 安装 Python 依赖（用国内镜像+预编译Wheel，快且稳）
RUN pip install --upgrade pip && \
    pip install --default-timeout=100 --prefer-binary \
    -i https://mirrors.aliyun.com/pypi/simple \
    -r requirements.txt

# 5. 复制项目代码（最后复制，代码改了不影响依赖缓存）
COPY . .

# 6. 暴露 FastAPI 运行的端口（默认 8000，和 uvicorn 启动端口对应）
EXPOSE 8000

# 7. 启动命令（uvicorn 启动 FastAPI，注意：需替换成你的入口文件名，比如 main.py）
# 格式：uvicorn 文件名:FastAPI实例名 --host 0.0.0.0 --port 端口
CMD ["python3", "api_fa.py"]
