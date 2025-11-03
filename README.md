# 利用Docker部署FastAPI在云服务器（文本生成与语音转换应用）

## 项目概述

本项目是一个基于FastAPI的Web服务，集成了文本生成和文本转语音功能。通过Docker容器化部署，可以实现跨平台、一键式部署和运行。

### 核心功能
- **文本生成**：使用阿里云DashScope API（通义千问模型）生成个性化回复
- **语音合成**：将生成的文本转换为语音文件（WAV格式）
- **RESTful API**：提供标准的HTTP接口供客户端调用
- **跨设备访问**：支持外部设备通过网络访问服务

## 项目结构

```
testapi/
├── api_fa.py              # 主FastAPI应用文件
├── apitext.py             # 文本生成模块
├── apilis.py              # 文本转语音模块
├── Dockerfile             # Docker构建配置
├── requirements.txt       # Python依赖包列表
├── client_received_audio.wav  # 客户端接收的音频示例
└── temp_audios/           # 临时音频文件存储目录
```

## 核心代码解析

### 1. 主应用 (api_fa.py) --fastapi

```python
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
import os
import io
import apitext

app = FastAPI(title="跨设备音频输出服务")

# 配置临时音频目录
TEMP_AUDIO_DIR = "./temp_audios"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

@app.get("/get-audio-direct", summary="直接返回生成的音频文件")
async def get_audio_direct(text: str = "输入询问文本："):
    # 调用文本生成和语音转换逻辑
    apitext.work_text(text)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    audio_path = os.path.join(current_dir, "downloaded_audio.wav")
    
    return FileResponse(
        path=audio_path,
        media_type="audio/wav",
        filename="fastapi_generated_audio.wav"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_fa:app", host="0.0.0.0", port=8000, reload=True)
```

### 2. 文本生成模块 (apitext.py)

```python
import os
import dashscope
import apilis

def work_text(text):
    # 添加角色设定前缀
    text = "你是小柚，是18岁台湾高中生，软萌台湾腔..." + text
    messages = [
        {'role':'system','content':'你是一个小萌妹'},
        {'role': 'user','content': text}
    ]
    
    # 调用阿里云DashScope API生成文本
    responses = dashscope.Generation.call(
        api_key=os.getenv('DASHSCOPE_API_KEY') or "you_api_key",
        model="qwen-plus",
        messages=messages,
        result_format='message',
        stream=True,
        incremental_output=True
    )
    
    re_text = ""
    for response in responses:
        re_text += response['output']['choices'][0]['message']['content']
    
    print(re_text)
    # 调用语音合成模块
    apilis.work_text(re_text)
```

### 3. 语音合成模块 (apilis.py)

```python
import os
import requests
import dashscope

def work_text(text : str):
    dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

    # 调用阿里云TTS API合成语音
    response = dashscope.MultiModalConversation.call(
        model="qwen3-tts-flash",
        api_key=os.getenv("DASHSCOPE_API_KEY") or "you_api_key",
        text=text,
        voice="Cherry",
        language_type="Chinese",
        stream=False
    )
    
    audio_url = response.output.audio.url
    save_path = "downloaded_audio.wav"

    # 下载生成的音频文件
    try:
        response = requests.get(audio_url)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        print(f"音频文件已保存至：{save_path}")
    except Exception as e:
        print(f"下载失败：{str(e)}")
```

## Docker部署配置

### Dockerfile

```dockerfile
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
# 也可以像下面一样
CMD ["python3", "api_fa.py"]
```

### 依赖文件 (requirements.txt)

```
fastapi>=0.104.1
uvicorn>=0.24.0
dashscope>=1.14.1
requests>=2.31.0
```

## 部署步骤

### 1. 构建Docker镜像

```bash
docker build -t fastapi-tts-app .
```

### 2. 运行Docker容器

```bash
docker run -d -p 8000:8000 --name fastapi-tts-container fastapi-tts-app
```

### 3. 验证服务运行

```bash
# 检查容器状态
docker ps

# 查看服务日志
docker logs fastapi-tts-container
```

### 3. 部署Docker在阿里仓库（为什么不在docker hub呢，当然是网络原因，我自己开魔法也搞不了所以就替代了）

先在阿里注册帐号
#### 登录
```python
docker login registry.cn-hangzhou.aliyuncs.com  # 地域不同，前缀不同（如 cn-shanghai、cn-beijing）

```
#### 把生成好的镜像tag进阿里仓库

```python
docker tag 本地镜像名:版本号 阿里云仓库地址:版本号
#docker tag my-app:v1.0 registry.cn-hangzhou.aliyuncs.com/my-docker-repo/my-app:v1.0
```
#### 在云服务器上拉取
```python
docker push registry.cn-hangzhou.aliyuncs.com/my-docker-repo/my-app:v1.0
```


## API使用说明

### 生成音频接口

**请求方式**: GET  
**接口地址**: `http://localhost:8000/get-audio-direct`  
**参数**: 
- `text` (可选): 输入文本，默认值为"输入询问文本："

**示例调用**:
```bash
curl "http://localhost:8000/get-audio-direct?text=你好，今天天气怎么样？"
```

**响应**: 直接返回WAV格式的音频文件下载

## 环境变量配置

项目使用阿里云DashScope API，需要配置API Key：

```bash
# 在运行容器时设置环境变量
docker run -d -p 8000:8000 \
  -e DASHSCOPE_API_KEY="your-api-key-here" \
  --name fastapi-tts-container \
  fastapi-tts-app

# 环境变量可用可不用，自己测试的话，可以在代码中加上，不然记得在run的时候加上环境变量（api_key）
```

## 调用示例

``` python
import requests

# 1. 配置服务端接口地址（替换为你的服务端IP）
SERVER_IP = "XXXXX"  # 服务端内网IP（同一局域网）或公网IP（外网），局域网的话就是 localhost , (就是在云服务器上的公网IP)
PORT = 8000

# 2. 场景：直接获取音频并保存到本地
def get_audio_direct(text="你是谁呀宝宝"):
    url = f"http://{SERVER_IP}:{PORT}/get-audio-direct"
    params = {"text": text}  # 传递生成音频的参数（如文本）
    response = requests.get(url, params=params)
    if response.status_code == 200:
        # 保存音频到本地
        with open("client_received_audio.wav", "wb") as f:
            f.write(response.content)
        print("音频获取成功，已保存为 client_received_audio.wav")
    else:
        print(f"获取失败：{response.text}")



get_audio_direct()  # 场景1：直接获取
```

## 注意事项

1. **API密钥安全**: 建议通过环境变量传递API密钥，避免在代码中硬编码
2. **网络要求**: 服务需要访问阿里云DashScope API，确保网络连接正常
3. **存储空间**: 音频文件会保存在容器内，长期运行需考虑存储管理
4. **性能优化**: 对于高并发场景，建议添加缓存机制和负载均衡
5. **错误处理**: 完善API调用失败时的错误处理和重试机制

## 扩展建议

1. **添加健康检查**: 在Dockerfile中添加健康检查端点
2. **日志管理**: 配置结构化日志和日志轮转
3. **监控告警**: 集成Prometheus和Grafana进行监控
4. **数据库集成**: 添加用户管理和历史记录功能
5. **前端界面**: 开发Web界面提升用户体验

通过Docker部署，本项目可以轻松地在任何支持Docker的环境中运行，实现了快速部署和水平扩展能力。
