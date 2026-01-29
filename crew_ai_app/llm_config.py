"""
LLM Configuration for CrewAI using AWS Bedrock.

CrewAI uses LiteLLM under the hood, which natively supports AWS Bedrock.
No need for LangChain - just configure environment variables!
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_bedrock_llm_config(
    model_id: Optional[str] = None,
    region: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 4096
) -> Dict[str, Any]:
    """Get AWS Bedrock LLM configuration for CrewAI agents.

    CrewAI uses LiteLLM which supports Bedrock natively via environment variables.
    This function returns the model string and kwargs that CrewAI expects.

    Args:
        model_id: Bedrock model ID (e.g., 'anthropic.claude-haiku-4-5-20251001-v1:0')
        region: AWS region for Bedrock (defaults to AWS_BEDROCK_REGION or AWS_REGION)
        temperature: Model temperature (0-1, lower is more deterministic)
        max_tokens: Maximum tokens in response

    Returns:
        Dict with 'model' string and 'llm_config' dict for CrewAI Agent

    Example:
        config = get_bedrock_llm_config()
        agent = Agent(
            role="...",
            goal="...",
            llm=config['model'],
            llm_config=config['llm_config']
        )
    """
    # Get configuration from environment variables
    model_id = model_id or os.getenv("AWS_BEDROCK_MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0")
    region = region or os.getenv("AWS_BEDROCK_REGION") or os.getenv("AWS_REGION", "us-east-1")

    # Verify AWS credentials are available
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    if not aws_access_key or not aws_secret_key:
        logger.warning("AWS credentials not found in environment variables. Relying on AWS credential chain.")

    logger.info(f"Configuring Bedrock LLM: model={model_id}, region={region}")

    # CrewAI/LiteLLM expects Bedrock models in format: "bedrock/<model_id>"
    litellm_model = f"bedrock/{model_id}"

    # LLM configuration for CrewAI
    llm_config = {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.9,
        "aws_region_name": region,
    }

    logger.info(f"Bedrock LLM configured: {litellm_model}")

    return {
        "model": litellm_model,
        "llm_config": llm_config
    }


# Available Bedrock models (as of 2025)
BEDROCK_MODELS = {
    # Anthropic Claude Models
    "claude-3-5-sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "claude-3-5-sonnet-v2": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "claude-3-5-haiku": "anthropic.claude-3-5-haiku-20241022-v1:0",
    "claude-3-7-sonnet": "anthropic.claude-3-7-sonnet-20250219-v1:0",
    "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "claude-sonnet-4-5": "anthropic.claude-sonnet-4-5-20250929-v1:0",
    "claude-sonnet-4": "anthropic.claude-sonnet-4-20250514-v1:0",
    "claude-opus-4-1": "anthropic.claude-opus-4-1-20250805-v1:0",
    "claude-opus-4": "anthropic.claude-opus-4-20250514-v1:0",
    "claude-haiku-4-5": "anthropic.claude-haiku-4-5-20251001-v1:0",
    "claude-2.1": "anthropic.claude-v2:1",
    "claude-2": "anthropic.claude-v2",
    "claude-instant": "anthropic.claude-instant-v1",

    # Amazon Nova Models
    "nova-micro": "amazon.nova-micro-v1:0",
    "nova-lite": "amazon.nova-lite-v1:0",
    "nova-pro": "amazon.nova-pro-v1:0",
    "nova-premier": "amazon.nova-premier-v1:0",
    "nova-canvas": "amazon.nova-canvas-v1:0",
    "nova-reel": "amazon.nova-reel-v1:0",
    "nova-sonic": "amazon.nova-sonic-v1:0",
}


def get_recommended_model() -> str:
    """Get the recommended Bedrock model for dispute resolution.

    Returns:
        Model ID for Claude 4.5 Haiku
    """
    return BEDROCK_MODELS["claude-haiku-4-5"]
