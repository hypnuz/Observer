# -*- coding: utf-8 -*-
import os
import logging
from flask import Flask, request, abort, render_template, escape
from wechatpy import parse_message, create_reply
from wechatpy.utils import check_signature
from wechatpy.exceptions import (
    InvalidSignatureException,
    InvalidAppIdException,
)
from main import MainLogic

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(filename='app.log',
                    level=logging.DEBUG, format=LOG_FORMAT)

# set token or get from environments
TOKEN = os.getenv("WECHAT_TOKEN", "123456")
AES_KEY = os.getenv("WECHAT_AES_KEY", "")
APPID = os.getenv("WECHAT_APPID", "")

app = Flask(__name__)
MAIN_LOGIC = MainLogic()

@app.route("/")
def index():
    host = request.url_root
    return render_template("index.html", host=host)

@app.route("/wx", methods=["GET", "POST"])
def wechat():
    signature = request.args.get("signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")
    encrypt_type = request.args.get("encrypt_type", "raw")
    msg_signature = request.args.get("msg_signature", "")
    try:
        check_signature(TOKEN, signature, timestamp, nonce)
    except InvalidSignatureException:
        abort(403)
    if request.method == "GET":
        echo_str = request.args.get("echostr", "")
        return escape(echo_str)

    # POST request
    if encrypt_type == "raw":
        # plaintext mode
        msg = parse_message(request.data)
        if msg.type == "text":
            reply_text = MAIN_LOGIC.handle_msg(msg)
            reply = create_reply(reply_text, msg)
        elif msg.type == "event":
            reply_text = MAIN_LOGIC.handle_event(msg)
            reply = create_reply(reply_text, msg)
        else:
            reply = create_reply("Sorry, can not handle this for now", msg)
        return reply.render()
    else:
        # encryption mode
        from wechatpy.crypto import WeChatCrypto

        crypto = WeChatCrypto(TOKEN, AES_KEY, APPID)
        try:
            msg = crypto.decrypt_message(request.data, msg_signature, timestamp, nonce)
        except (InvalidSignatureException, InvalidAppIdException):
            abort(403)
        else:
            msg = parse_message(msg)
            if msg.type == "text":
                reply = create_reply(msg.content, msg)
            else:
                reply = create_reply("Sorry, can not handle this for now", msg)
            return crypto.encrypt_message(reply.render(), nonce, timestamp)


if __name__ == "__main__":
    app.run("0.0.0.0", 80, debug=False, use_reloader=False)
    logging.info(">> service start!")
