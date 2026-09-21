"""Shared configuration for the multi-agent system."""

import os
from dotenv import load_dotenv

load_dotenv()

# GCP Configuration
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
BUCKET_URI = os.environ.get("BUCKET_URI")


def validate_config():
    """Validate required configuration is set."""
    required = {
        "GOOGLE_CLOUD_PROJECT": GOOGLE_CLOUD_PROJECT,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Check your .env file."
        )
    return True
