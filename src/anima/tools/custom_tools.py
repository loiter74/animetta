"""
自定义工具集合

提供额外的实用工具。
"""

from loguru import logger
from langchain_core.tools import tool


@tool
async def url_preview(url: str) -> str:
    """获取 URL 预览和摘要

    Args:
        url: 要预览的 URL

    Returns:
        str: URL 预览信息
    """
    import httpx
    from urllib.parse import urlparse

    try:
        # 验证 URL 格式
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return f"Invalid URL: {url}"

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200:
                # 获取页面内容
                html = response.text

                # 简单提取标题和部分内容
                title = "Unknown"
                if "<title>" in html:
                    start = html.find("<title>") + 7
                    end = html.find("</title>", start)
                    title = html[start:end].strip()

                # 获取前 500 个字符作为预览
                import re
                text_only = re.sub(r'<[^>]+>', ' ', html)
                text_only = ' '.join(text_only.split())
                preview = text_only[:500] + "..." if len(text_only) > 500 else text_only

                result = f"URL Preview: {url}\n"
                result += f"Title: {title}\n"
                result += f"Status: {response.status_code}\n"
                result += f"Content-Type: {response.headers.get('content-type', 'unknown')}\n"
                result += f"Preview:\n{preview}"

                logger.info(f"[url_preview] Success: {url}")
                return result
            else:
                return f"Failed to fetch URL: {url} (status {response.status_code})"

    except Exception as e:
        logger.error(f"[url_preview] Failed: {e}")
        return f"Failed to preview URL: {str(e)}"


@tool
async def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件（需要 SMTP 配置）

    Args:
        to: 收件人邮箱
        subject: 邮件主题
        body: 邮件正文

    Returns:
        str: 发送结果
    """
    import os
    import smtplib
    from email.message import EmailMessage

    # SMTP 配置
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        return "Email not configured. Please set SMTP_USER and SMTP_PASSWORD environment variables.\n\nExample for Gmail:\n1. Enable 2FA on your Google account\n2. Generate App Password\n3. Set SMTP_USER=your@gmail.com\n4. Set SMTP_PASSWORD=your_app_password"

    try:
        # 创建邮件
        msg = EmailMessage()
        msg["From"] = smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        # 发送邮件
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        logger.info(f"[send_email] Email sent to {to}")
        return f"Email sent successfully to {to}"

    except Exception as e:
        logger.error(f"[send_email] Failed: {e}")
        return f"Failed to send email: {str(e)}"


@tool
async def image_gen(prompt: str, size: str = "1024x1024") -> str:
    """生成图片（需要 API Key）

    Args:
        prompt: 图片描述提示词
        size: 图片尺寸（256x256, 512x512, 1024x1024）

    Returns:
        str: 图片 URL 或生成结果
    """
    import os
    import httpx

    # OpenAI DALL-E
    openai_key = os.getenv("OPENAI_API_KEY")

    if openai_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    json={
                        "model": "dall-e-3",
                        "prompt": prompt,
                        "n": 1,
                        "size": size,
                    },
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    image_url = data["data"][0]["url"]
                    logger.info(f"[image_gen] DALL-E success")
                    return f"Image generated!\nPrompt: {prompt}\nURL: {image_url}\n\nNote: URL expires in 1 hour."
                else:
                    logger.warning(f"[image_gen] DALL-E error: {response.status_code}")
        except Exception as e:
            logger.warning(f"[image_gen] DALL-E failed: {e}")

    # Stable Diffusion (通过 replicate)
    replicate_key = os.getenv("REPLICATE_API_TOKEN")

    if replicate_key:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 创建预测
                response = await client.post(
                    "https://api.replicate.com/v1/predictions",
                    json={
                        "version": "stability-ai/sdxl",
                        "input": {"prompt": prompt},
                    },
                    headers={
                        "Authorization": f"Bearer {replicate_key}",
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    if data.get("status") == "starting":
                        # 需要轮询获取结果
                        get_url = data.get("urls", {}).get("get")
                        if get_url:
                            get_response = await client.get(
                                get_url,
                                headers={"Authorization": f"Bearer {replicate_key}"},
                            )
                            result = get_response.json()
                            image_url = result.get("output")
                            if image_url:
                                return f"Image generated!\nPrompt: {prompt}\nURL: {image_url}"
        except Exception as e:
            logger.warning(f"[image_gen] Replicate failed: {e}")

    return "Image generation unavailable. Please set OPENAI_API_KEY (DALL-E) or REPLICATE_API_TOKEN (Stable Diffusion).\n\nDALL-E: https://platform.openai.com/api-keys\nReplicate: https://replicate.com/account/api-tokens"


# 导出工具列表
CUSTOM_TOOLS = [url_preview, send_email, image_gen]


def get_custom_tools() -> list:
    """获取所有自定义工具"""
    return CUSTOM_TOOLS.copy()
