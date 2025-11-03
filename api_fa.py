from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
import os
import io
import apitext
# 1. 初始化 FastAPI，关键：启动时绑定 0.0.0.0（允许外部设备访问）
app = FastAPI(title="跨设备音频输出服务")

# 配置：临时音频保存路径（若生成在内存可不用）
TEMP_AUDIO_DIR = "./temp_audios"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)


# 3. 核心2：对外提供音频的接口（客户端请求此接口获取音频）
@app.get("/get-audio-direct", summary="直接返回生成的音频文件（客户端请求即下载）")
async def get_audio_direct(text: str = "输入询问文本："):
    # 步骤1：生成音频（调用你的音频生成逻辑）
    apitext.work_text(text)
    current_dir = os.path.dirname(os.path.abspath(__file__))
# 拼接相对路径（在代码目录下创建 temp_audios 文件夹，保存音频）
    audio_path = os.path.join(current_dir, "downloaded_audio.wav")
    
    # 步骤2：直接返回音频文件（客户端请求后自动下载，支持浏览器播放）
    return FileResponse(
        path=audio_path,
        media_type="audio/wav",  # 音频 MIME 类型，WAV 对应 audio/wav，MP3 对应 audio/mpeg
        filename="fastapi_generated_audio.wav"  # 客户端下载时的默认文件名
    )


if __name__ == "__main__":
    # 关键：启动服务时 host=0.0.0.0（允许所有设备访问），port=8000（可自定义，需开放端口）
    import uvicorn
    uvicorn.run("api_fa:app", host="0.0.0.0", port=8000, reload=True)
