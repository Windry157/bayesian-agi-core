"""
模型自检 — 启动时确保所需模型在 Ollama 上可用，缺失则自动拉取
"""

import logging
import httpx

logger = logging.getLogger(__name__)

REQUIRED_EMBED_MODELS = ["nomic-embed-text", "nomic-embed-text-v2-moe", "embeddinggemma"]


async def ensure_models(ollama_url: str, model_name: str, embed_model: str):
    """确保指定模型在 Ollama 上可用，嵌入模型缺失则自动拉取"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            data = resp.json()
            available = {m["name"] for m in data.get("models", [])}
    except Exception as e:
        logger.warning(f"无法连接 Ollama ({ollama_url}): {e}")
        return

    # 检查主模型
    if model_name not in available:
        logger.warning(f"主模型 {model_name} 不在 Ollama 中，请手动拉取: ollama pull {model_name}")

    # 检查嵌入模型 — 必须有一个用于记忆检索
    embed_found = None
    for candidate in REQUIRED_EMBED_MODELS:
        if candidate in available:
            embed_found = candidate
            break

    if embed_found:
        logger.info(f"嵌入模型 {embed_found} 已就绪")
        return

    # 自动拉取
    target = embed_model.split(":")[-1] if ":" in embed_model else embed_model
    # 尝试按 config 中的名称匹配
    if embed_model in available:
        return
    # 尝试已知别名
    for candidate in REQUIRED_EMBED_MODELS:
        if candidate in embed_model or embed_model in candidate:
            target = candidate
            if target in available:
                logger.info(f"嵌入模型 {target} 匹配成功")
                return

    # 拉取最轻量的
    pull_model = "nomic-embed-text"
    logger.info(f"嵌入模型缺失，自动拉取 {pull_model}...")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{ollama_url}/api/pull",
                json={"name": pull_model, "stream": False},
            )
        if resp.status_code == 200:
            logger.info(f"嵌入模型 {pull_model} 拉取成功")
        else:
            logger.warning(f"拉取 {pull_model} 失败: {resp.status_code}")
    except Exception as e:
        logger.warning(f"拉取嵌入模型失败: {e}")
