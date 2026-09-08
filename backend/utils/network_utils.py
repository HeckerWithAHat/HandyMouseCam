"""
Network utilities for HandyMouseCam.
Handles IP detection and network configuration.
"""

import logging
import socket
from typing import Optional

logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """
    Get local IP address of the machine.
    Attempts to find the non-loopback IPv4 address.
    
    Returns:
        str: Local IP address (e.g., "192.168.1.100")
    """
    try:
        logger.debug("Detecting local IP address...")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            address = sock.getsockname()[0]
            if address and not address.startswith("127."):
                return address

        hostname_address = socket.gethostbyname(socket.gethostname())
        if hostname_address and not hostname_address.startswith("127."):
            return hostname_address
    except OSError as error:
        logger.warning("Could not detect a LAN IP address: %s", error)

    return "127.0.0.1"



def test_network_connectivity(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Test if a network host is reachable.
    
    Args:
        host: Host address
        port: Port number
        timeout: Timeout in seconds
        
    Returns:
        bool: True if reachable
    """
    # TODO: Implement connectivity test
    logger.debug(f"Testing connectivity to {host}:{port}")

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            return True
    except (socket.timeout, socket.error) as e:
        logger.warning(f"Failed to connect to {host}:{port}: {e}")

    return False
