"""Database package for dispute resolution system."""

from .dynamo_client import DynamoDBClient

__all__ = ["DynamoDBClient"]