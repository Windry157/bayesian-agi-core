import asyncio, os
import itchat
from itchat.content import TEXT
from src.core.assistant import Assistant

assistant = Assistant()


def qr_callback(uuid, status, qrcode):
    path = os.path.join(os.path.dirname(__file__) or ".", "qrcode.png")
    with open(path, "wb") as f:
        f.write(qrcode)
    print(f"二维码已保存到: {path}，请用微信扫码登录")


@itchat.msg_register(TEXT)
def handle_text(msg):
    user_id = f"wechat-{msg['FromUserName']}"
    result = asyncio.run(assistant.process_with_context(msg["Text"], user_id))
    return result.get("response", "抱歉，处理出错")


if __name__ == "__main__":
    itchat.auto_login(hotReload=True, qrCallback=qr_callback)
    itchat.run()
