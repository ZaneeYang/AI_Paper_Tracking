"""
企业微信消息推送（群机器人 Webhook）。
文档：https://developer.work.weixin.qq.com/document/path/91770
限制：每条 Markdown ≤ 4096 字节，每分钟 ≤ 20 条。
"""
import logging
import time
from typing import List

import requests

logger = logging.getLogger(__name__)


def send_markdown_messages(webhook_url: str, messages: List[str]) -> bool:
    """
    按顺序向企业微信群推送多条 Markdown 消息。
    每条之间间隔 1 秒以避免触发频率限制（20 条/分钟）。
    返回是否全部发送成功。
    """
    if not webhook_url or not webhook_url.strip():
        logger.warning("未配置企业微信 Webhook URL，跳过推送")
        return False

    webhook_url = webhook_url.strip()
    all_ok = True

    for idx, content in enumerate(messages, 1):
        size = len(content.encode("utf-8"))
        logger.info("企业微信推送第 %d/%d 条（%d 字节）", idx, len(messages), size)

        payload = {"msgtype": "markdown", "markdown": {"content": content}}
        try:
            resp = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            data = resp.json()
            if data.get("errcode") == 0:
                logger.info("第 %d 条推送成功", idx)
            else:
                logger.warning(
                    "第 %d 条推送失败: errcode=%s errmsg=%s",
                    idx, data.get("errcode"), data.get("errmsg"),
                )
                all_ok = False
        except requests.RequestException as e:
            logger.warning("第 %d 条推送请求异常: %s", idx, e)
            all_ok = False

        # 多条消息之间等 1 秒，避免触发限频
        if idx < len(messages):
            time.sleep(1)

    return all_ok
