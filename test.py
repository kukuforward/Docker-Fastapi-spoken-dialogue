# 导入必要的Python模块
import logging  # 日志记录模块
import os       # 操作系统接口模块
import base64   # Base64编码解码模块
import signal   # 信号处理模块
import sys      # 系统相关参数和函数
import time     # 时间相关操作
import pyaudio  # 音频输入输出模块，用于麦克风录音
import dashscope  # 阿里云DashScope SDK
import api_work
# 导入DashScope语音识别相关模块
from dashscope.audio.qwen_omni import *
from dashscope.audio.qwen_omni.omni_realtime import TranscriptionParams
import pygame


api_work.work_text("你好呀,你有什么问题嘛？")


def play_wav(wav_path):
    """
    播放 WAV 文件
    :param wav_path: WAV 文件路径（相对/绝对路径）
    """
    # 初始化 pygame 混音器（专门用于音频播放）
    pygame.mixer.init()

    try:
        # 1. 检查 WAV 文件是否存在
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"WAV 文件不存在：{wav_path}")
        
        # 2. 加载 WAV 文件（pygame 自动处理 WAV 解码）
        pygame.mixer.music.load(wav_path)
        print(f"🎵 开始播放：{wav_path}")
        
        # 3. 播放 WAV（block=False 表示非阻塞播放，后续需等待播放完成）
        pygame.mixer.music.play()
        
        # 4. 等待播放完成（循环检查播放状态，避免提前删除）
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)  # 每 0.1 秒检查一次，不占用过多资源
        
        print("✅ 播放完成")

    # 捕获常见异常
    except FileNotFoundError as e:
        print(f"❌ 错误：{e}")
    except pygame.error as e:
        print(f"❌ 音频播放错误（可能是文件格式不支持）：{e}")
    except Exception as e:
        print(f"❌ 未知错误：{str(e)}")
    finally:
        # 无论是否成功，都关闭 pygame 混音器，释放资源
        pygame.mixer.quit()


def play_wav_and_delete(wav_path):
    """
    播放 WAV 文件，播放完成后删除文件
    :param wav_path: WAV 文件路径（相对/绝对路径）
    """
    # 初始化 pygame 混音器（专门用于音频播放）
    pygame.mixer.init()

    try:
        # 1. 检查 WAV 文件是否存在
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"WAV 文件不存在：{wav_path}")
        
        # 2. 加载 WAV 文件（pygame 自动处理 WAV 解码）
        pygame.mixer.music.load(wav_path)
        print(f"🎵 开始播放：{wav_path}")
        
        # 3. 播放 WAV（block=False 表示非阻塞播放，后续需等待播放完成）
        pygame.mixer.music.play()
        
        # 4. 等待播放完成（循环检查播放状态，避免提前删除）
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)  # 每 0.1 秒检查一次，不占用过多资源
        
        print("✅ 播放完成，准备删除文件")
        
        # 5. 播放完成后，删除 WAV 文件
        os.remove(wav_path)
        print(f"🗑️  成功删除文件：{wav_path}")

    # 捕获常见异常
    except FileNotFoundError as e:
        print(f"❌ 错误：{e}")
    except pygame.error as e:
        print(f"❌ 音频播放错误（可能是文件格式不支持）：{e}")
    except PermissionError:
        print(f"❌ 错误：权限不足，无法删除文件 → {wav_path}")
    except Exception as e:
        print(f"❌ 未知错误：{str(e)}")
    finally:
        # 无论是否成功，都关闭 pygame 混音器，释放资源
        pygame.mixer.quit()



def setup_logging():
    """
    配置日志输出设置
    
    返回:
        logger: 配置好的日志记录器实例
    """
    # 创建dashscope专用的日志记录器
    logger = logging.getLogger('dashscope')
    logger.setLevel(logging.DEBUG)  # 设置日志级别为DEBUG
    
    # 创建控制台处理器，输出到标准输出
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    
    # 设置日志格式：时间戳 - 日志器名称 - 日志级别 - 日志消息
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # 将处理器添加到日志记录器
    logger.addHandler(handler)
    logger.propagate = False  # 防止日志向上传播到根日志记录器
    
    return logger


def init_api_key():
    """
    初始化API Key配置
    
    从环境变量DASHSCOPE_API_KEY获取API密钥，
    如果没有设置则使用默认占位符并显示警告
    """
    # 从环境变量获取API Key，如果没有则使用默认值
    dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', 'you_api_key')
    
    # 检查是否使用了占位符API Key
    if dashscope.api_key == 'YOUR_API_KEY':
        print('[Warning] Using placeholder API key, set DASHSCOPE_API_KEY environment variable.')


class MyCallback(OmniRealtimeCallback):
    """
    实时语音识别回调处理类
    
    继承自OmniRealtimeCallback，用于处理实时语音识别过程中的各种事件
    """
    def __init__(self, conversation):
        """
        初始化回调处理器
        
        参数:
            conversation: OmniRealtimeConversation实例，用于与服务器通信
        """
        self.conversation = conversation
        # 定义事件类型与处理函数的映射关系
        self.handlers = {
            'session.created': self._handle_session_created,  # 会话创建事件
            'conversation.item.input_audio_transcription.completed': self._handle_final_text,  # 最终识别文本事件
            'conversation.item.input_audio_transcription.text': self._handle_stash_text,  # 临时识别文本事件
            'input_audio_buffer.speech_started': lambda r: print('======Speech Start======'),  # 语音开始事件
            'input_audio_buffer.speech_stopped': lambda r: print('======Speech Stop======'),  # 语音结束事件
            'response.done': self._handle_response_done  # 响应完成事件
        }
        
        # 关键词检测和文本记录相关变量
        self.keywords = ["你好小度", "小爱同学", "天猫精灵", "你好，小度。"]  # 要检测的关键词列表
        self.is_recording = False  # 是否正在记录文本
        self.recorded_texts = []  # 存储检测到关键词后的文本
        self.recording_start_time = None  # 开始记录的时间
        self.recording_duration = 2  # 记录时长（秒）

    def on_open(self):
        """
        WebSocket连接建立时的回调函数
        
        当与语音识别服务建立WebSocket连接时自动调用
        """
        print('Connection opened')  # 打印连接建立信息

    def on_close(self, code, msg):
        """
        WebSocket连接关闭时的回调函数
        
        参数:
            code: 关闭代码，表示连接关闭的原因
            msg: 关闭消息，提供额外的关闭信息
        """
        print(f'Connection closed, code: {code}, msg: {msg}')  # 打印连接关闭详情

    def on_event(self, response):
        """
        处理从服务器接收到的所有事件
        
        根据事件类型分发到对应的处理函数
        
        参数:
            response: 服务器返回的事件响应数据，包含事件类型和相关信息
        """
        try:
            # 根据事件类型获取对应的处理函数
            handler = self.handlers.get(response['type'])
            if handler:
                handler(response)  # 调用对应的处理函数
        except Exception as e:
            print(f'[Error] {e}')  # 打印异常信息，确保程序不会因单个事件处理失败而崩溃

    def _handle_session_created(self, response):
        """
        处理会话创建事件
        
        当语音识别服务成功创建新会话时调用
        
        参数:
            response: 包含会话信息的响应数据
        """
        print(f"Start session: {response['session']['id']}")  # 打印新创建的会话ID

    def _handle_final_text(self, response):
        """
        处理最终识别文本事件
        
        当语音识别完成并返回最终识别结果时调用，包含关键词检测逻辑
        
        参数:
            response: 包含最终识别文本的响应数据
        """
        final_text = response['transcript']
        print(f"Final recognized text: {final_text}")  # 打印最终识别结果
        
        # 关键词检测逻辑
        if not self.is_recording:
            # 检查是否包含关键词
            for keyword in self.keywords:
                if keyword in final_text:
                    play_wav("hello.wav")
                    print(f"检测到关键词: '{keyword}'，开始记录'{self.recording_duration}'秒内的文本...")
                    self.start_recording()
                    break
        
        # 如果正在记录模式，保存文本
        if self.is_recording:
            self.recorded_texts.append({
                'timestamp': time.time(),
                'text': final_text
            })
            # 检查是否超过记录时长
            if time.time() - self.recording_start_time >= self.recording_duration:
                self.stop_recording()

    def _handle_stash_text(self, response):
        """
        处理临时识别文本事件
        
        当语音识别过程中产生中间结果时调用，用于实时显示识别进度
        
        参数:
            response: 包含临时识别文本的响应数据
        """
        # if(response['stash'] == '你好'):  # 检查是否有临时结果
        #     print("Received expected stash result '你好库库'")
        #     print("测试通过"*20)

    def _handle_response_done(self, response):
        """
        处理响应完成事件
        
        当整个语音识别响应过程完成时调用，显示性能指标
        
        参数:
            response: 响应完成事件的响应数据
        """
        print('======RESPONSE DONE======')  # 响应完成分隔符
        # 打印性能指标：响应ID、首次文本延迟、首次音频延迟
        print(f"[Metric] response: {self.conversation.get_last_response_id()}, "
              f"first text delay: {self.conversation.get_last_first_text_delay()}, "
              f"first audio delay: {self.conversation.get_last_first_audio_delay()}")

    def start_recording(self):
        """
        开始记录文本
        
        当检测到关键词时调用，开始记录后续秒内的所有识别文本
        """
        self.is_recording = True
        self.recording_start_time = time.time()
        self.recorded_texts = []  # 清空之前的记录
        print(f"开始记录文本，将持续{self.recording_duration}秒...")

    def stop_recording(self):
        """
        停止记录文本并保存到文件
        
        当记录时间达到设定时长时自动调用，将记录的文本保存到文件
        """
        self.is_recording = False
        print("记录结束，正在保存文本...")
        
        # 生成文件名：关键词检测_时间戳.txt
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"语音文本.txt"
        
        # 保存文本到文件
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # f.write(f"关键词检测记录 - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                # f.write(f"记录时长: {self.recording_duration}秒\n")
                # f.write("=" * 50 + "\n\n")
                
                for item in self.recorded_texts:
                    time_str = time.strftime('%H:%M:%S', time.localtime(item['timestamp']))
                    f.write(f"{item['text']}\n")
            
            print(f"文本已保存到文件: {filename}")
            print(f"共记录了 {len(self.recorded_texts)} 条文本")
            
            # 在控制台显示记录的内容摘要

            content = []
            file_path = filename
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:  # 逐行读取
                    content.append(line)
            os.remove(file_path)
            content = ''.join(content)  # 拼接成完整内容
            text = ""
            for i in content:
                text += i + '。'
            api_work.get_audio_direct(text=text)
            play_wav("work_v.wav")
            if self.recorded_texts:
                print("\n记录内容摘要:")
                for i, item in enumerate(self.recorded_texts[:5], 1):  # 显示前5条
                    time_str = time.strftime('%H:%M:%S', time.localtime(item['timestamp']))
                    print(f"  {i}. [{time_str}] {item['text']}")
                if len(self.recorded_texts) > 5:
                    print(f"  ... 还有 {len(self.recorded_texts) - 5} 条记录")
                    
        except Exception as e:
            print(f"保存文件时出错: {e}")
        
        # 重置记录状态
        self.recorded_texts = []
        self.recording_start_time = None
        
        # 添加等待时间，确保处理完成后再继续监听


def record_from_microphone(conversation, chunk_size=3200, sample_rate=16000):
    """
    从麦克风录制音频并实时发送到语音识别服务
    
    参数:
        conversation: OmniRealtimeConversation实例
        chunk_size: 每次读取的音频块大小，默认为3200字节
        sample_rate: 采样率，默认为16000Hz
    
    返回:
        None
    """
    # 初始化PyAudio
    pa = pyaudio.PyAudio()
    
    # 打开音频流
    audio_stream = pa.open(
        format=pyaudio.paInt16,      # 16位采样
        channels=1,                  # 单声道
        rate=sample_rate,            # 采样率
        input=True,                  # 输入流（麦克风）
        frames_per_buffer=chunk_size # 每次读取的帧数
    )
    
    print("开始从麦克风录制音频...")
    print("请开始说话（按Ctrl+C停止录制）")
    
    try:
        while True:
            # 从麦克风读取音频数据
            audio_data = audio_stream.read(chunk_size, exception_on_overflow=False)
            
            # 将音频数据转换为Base64编码
            audio_b64 = base64.b64encode(audio_data).decode('ascii')
            
            # 发送到语音识别服务
            conversation.append_audio(audio_b64)
            
    except KeyboardInterrupt:
        print("\n停止录制")
    finally:
        # 关闭音频流
        audio_stream.stop_stream()
        audio_stream.close()
        pa.terminate()


def main():
    """
    主函数 - 语音识别程序的入口点
    
    初始化日志、API密钥，建立WebSocket连接并进行实时语音识别
    """
    setup_logging()  # 配置日志系统
    init_api_key()   # 初始化API密钥
    
    # 创建实时语音识别会话
    conversation = OmniRealtimeConversation(
        model='qwen3-asr-flash-realtime',  # 使用快速实时语音识别模型
        # 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime
        url='wss://dashscope.aliyuncs.com/api-ws/v1/realtime',  # WebSocket服务地址
        callback=MyCallback(conversation=None)  # 暂时传None，稍后注入
    )

    # 注入自身到回调，解决循环依赖问题
    conversation.callback.conversation = conversation

    def handle_exit(sig, frame):
        """
        Ctrl+C信号处理函数，用于优雅退出程序
        
        参数:
            sig: 信号编号
            frame: 当前堆栈帧
        """
        print('Ctrl+C pressed, exiting...')
        conversation.close()  # 关闭WebSocket连接
        sys.exit(0)  # 退出程序

    signal.signal(signal.SIGINT, handle_exit)

    conversation.connect()  # 连接到语音识别服务

    # 配置语音识别参数
    transcription_params = TranscriptionParams(
        language='zh',           # 识别语言：中文
        sample_rate=16000,       # 采样率：16kHz
        input_audio_format="pcm" # 输入音频格式：PCM
        # 输入音频的语料，用于辅助识别
        # corpus_text=""
    )

    # 更新会话配置
    conversation.update_session(
        output_modalities=[MultiModality.TEXT],  # 输出模式：文本
        enable_input_audio_transcription=True,   # 启用语音识别
        transcription_params=transcription_params  # 应用识别参数
    )

    try:
        # 从麦克风录制并发送音频数据进行实时识别
        record_from_microphone(conversation)
    except Exception as e:
        print(f"Error occurred: {e}")  # 打印异常信息
    finally:
        conversation.close()  # 确保连接被关闭
        print("语音识别完成.")  # 处理完成提示


if __name__ == '__main__':
    """
    程序入口点
    
    当直接运行此脚本时执行main函数
    """
    main()
