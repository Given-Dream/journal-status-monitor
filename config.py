import os

class Config:
    # 期刊登录凭据
    IEEE_USERNAME = os.getenv("IEEE_USERNAME")
    IEEE_PASSWORD = os.getenv("IEEE_PASSWORD")
    IEEE_URL = os.getenv("IEEE_URL", "https://mc.manuscriptcentral.com/ieee-jlt") # 提供默认值

    ELSEVIER_USERNAME = os.getenv("ELSEVIER_USERNAME")
    ELSEVIER_PASSWORD = os.getenv("ELSEVIER_PASSWORD")
    ELSEVIER_URL = os.getenv("ELSEVIER_URL", "https://www.elsevier.com/login") # 提供默认值

    # 邮件配置
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587)) # 默认使用587端口

    # 数据文件路径
    DATA_FILE = "data/manuscripts.json"

    # 测试模式 (True: 使用模拟数据, False: 实际抓取)
    TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

    # 浏览器是否无头模式
    HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

    @staticmethod
    def get_smtp_config():
        return Config.SMTP_SERVER, Config.SMTP_PORT
