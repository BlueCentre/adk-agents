import logging
import platform

from google.adk.tools import FunctionTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OSInfoOutput(BaseModel):
    """Output model for the get_os_info tool."""

    system: str = Field(description="Operating system name (e.g., 'Linux', 'Darwin', 'Windows').")
    release: str = Field(description="Operating system release (e.g., '5.15.0-78-generic').")
    version: str = Field(description="Operating system version.")
    machine: str = Field(description="Machine hardware name (e.g., 'x86_64').")


def get_os_info() -> OSInfoOutput:
    """Gets basic operating system information."""
    logger.info("Getting operating system information.")
    try:
        return OSInfoOutput(system=platform.system(), release=platform.release(), version=platform.version(), machine=platform.machine())
    except Exception as e:
        logger.exception(f"Failed to get OS info: {e}")
        # Return placeholder values on error
        return OSInfoOutput(system="Unknown", release="Unknown", version="Unknown", machine="Unknown")


# Wrap get_os_info with FunctionTool
get_os_info_tool = FunctionTool(get_os_info)
