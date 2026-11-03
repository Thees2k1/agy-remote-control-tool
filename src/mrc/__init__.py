"""
Mobile Remote Control (MRC) Package
Out-of-band authorization and hybrid ask-first guardrails for Google Antigravity.
"""

from .cloud_remote import (
    parse_instance_name,
    get_cloud_remote_status,
    start_cloud_remote,
    broadcast_cloud_remote_url,
    CLOUD_REMOTE_BASE_URL
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "parse_instance_name",
    "get_cloud_remote_status",
    "start_cloud_remote",
    "broadcast_cloud_remote_url",
    "CLOUD_REMOTE_BASE_URL",
]
