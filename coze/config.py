# Coze API 配置
PERSONAL_TOKEN = "pat_IwcfOMzthfu4XWD0tvm0LlA00ZtALRu3dhlBFxmPs89hUseFu9Ctah9n18xgOUL9"  # 个人访问令牌

# 空间ID配置
SPACE_ID = "7449214369415675943"  # 空间ID

# 各工作流ID配置
WORKFLOW_IDS = {
    "word_to_sentence": "7483464718079180834",  # 单词到句子工作流
    "word_to_image": "7483367245570539571",  # 单词到图片工作流
    "sentence_to_image": "7484918741956952083", # 句子到图片工作流
    # "image_transformation": "",  # 未来可能添加：图片转换工作流
}

# 执行配置
DEFAULT_ASYNC = True  # 默认使用异步执行（仅限专业版用户）
DEFAULT_POLL_MAX_ATTEMPTS = 20  # 默认轮询最大尝试次数
DEFAULT_POLL_INTERVAL = 5  # 默认轮询间隔（秒）

# 飞书API配置
FEISHU_APP_ID = "cli_a769cd7901ac100e"
FEISHU_APP_SECRET = "JaCmFgaAoqvqYnvEiwKBQb2DW5F7CzFf"

# 调试级别
DEBUG = True 