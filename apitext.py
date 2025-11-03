import os
import dashscope
import apilis

def work_text(text):
    text = "你是小度” 是 18 岁台湾高中生，软萌台湾腔，爱收集小物件、有奶茶先吸珍珠等癖好，对话带生活场景，互动软萌不生硬：注意不要加括号和表情符号表示情感，字数控制在100以内" + text
    messages = [
        {'role':'system','content':'你是一个小萌妹'},
        {'role': 'user','content': text}
    ]
    responses = dashscope.Generation.call(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
        api_key=os.getenv('DASHSCOPE_API_KEY') or "api_key",
        model="qwen-plus", # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        messages=messages,
        result_format='message',
        stream=True,
        incremental_output=True
        )
    re_text = ""
    for response in responses:
        # print(response['output']['choices'][0]['message']['content'], end='', flush=True)  
        re_text += response['output']['choices'][0]['message']['content']
    print(re_text)
    apilis.work_text(re_text)
    

