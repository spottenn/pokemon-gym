"""
WSL utilities for dynamic host configuration
"""
import socket
import subprocess
import logging
import os

logger = logging.getLogger(__name__)


def get_windows_host_ip() -> str:
    """
    Get the Windows host IP address from within WSL.
    
    This function tries multiple methods and tests connectivity to find the working IP:
    1. Parse /etc/resolv.conf for nameserver
    2. Use hostname command to derive gateway
    3. Test common WSL2 defaults
    4. Return the first IP that works for Ollama connectivity
    
    Returns:
        str: The Windows host IP address that actually works
    """
    candidate_ips = []
    
    try:
        # Method 1: Parse /etc/resolv.conf (most reliable for WSL2)
        if os.path.exists('/etc/resolv.conf'):
            with open('/etc/resolv.conf', 'r') as f:
                for line in f:
                    if line.startswith('nameserver'):
                        ip = line.split()[1].strip()
                        candidate_ips.append(ip)
                        logger.info(f"Found potential Windows host IP from /etc/resolv.conf: {ip}")
    except Exception as e:
        logger.warning(f"Failed to read /etc/resolv.conf: {e}")
    
    try:
        # Method 2: Use hostname command to get gateway
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Get the first IP and derive gateway (usually .1)
            wsl_ip = result.stdout.strip().split()[0]
            # Convert 172.x.y.z to 172.x.y.1
            ip_parts = wsl_ip.split('.')
            if len(ip_parts) == 4:
                gateway_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1"
                candidate_ips.append(gateway_ip)
                logger.info(f"Derived potential Windows host IP from WSL IP {wsl_ip}: {gateway_ip}")
    except Exception as e:
        logger.warning(f"Failed to get IP from hostname: {e}")
    
    # Method 3: Add common defaults (localhost first for Windows compatibility)
    common_ips = ["127.0.0.1", "172.31.160.1", "172.17.0.1", "192.168.65.1"]
    for ip in common_ips:
        if ip not in candidate_ips:
            candidate_ips.append(ip)
    
    # Test each IP to find the working one
    logger.info(f"Testing {len(candidate_ips)} candidate IPs: {candidate_ips}")
    for ip in candidate_ips:
        if _test_ip_connectivity(ip):
            logger.info(f"Found working Windows host IP: {ip}")
            return ip
    
    # If no IP works, return the first candidate (likely from resolv.conf)
    fallback_ip = candidate_ips[0] if candidate_ips else "172.31.160.1"
    logger.warning(f"No working IP found, using fallback: {fallback_ip}")
    return fallback_ip


def _test_ip_connectivity(ip: str) -> bool:
    """
    Test if an IP has basic connectivity (ping test).
    
    Args:
        ip: The IP address to test
        
    Returns:
        bool: True if IP is reachable
    """
    try:
        # Use ping with timeout to test basic connectivity
        result = subprocess.run(['ping', '-c', '1', '-W', '2', ip], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def get_ollama_endpoint() -> str:
    """
    Get the Ollama endpoint URL for WSL by finding a working Windows host IP.
    
    Returns:
        str: The complete Ollama endpoint URL
    """
    # Get candidate IPs the same way as get_windows_host_ip but test Ollama specifically
    candidate_ips = []
    
    try:
        # Parse /etc/resolv.conf
        if os.path.exists('/etc/resolv.conf'):
            with open('/etc/resolv.conf', 'r') as f:
                for line in f:
                    if line.startswith('nameserver'):
                        ip = line.split()[1].strip()
                        candidate_ips.append(ip)
    except Exception:
        pass
    
    try:
        # Derive from WSL IP
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            wsl_ip = result.stdout.strip().split()[0]
            ip_parts = wsl_ip.split('.')
            if len(ip_parts) == 4:
                gateway_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1"
                candidate_ips.append(gateway_ip)
    except Exception:
        pass
    
    # Add common defaults (localhost first for Windows compatibility)
    common_ips = ["127.0.0.1", "172.31.160.1", "172.17.0.1", "192.168.65.1"]
    for ip in common_ips:
        if ip not in candidate_ips:
            candidate_ips.append(ip)
    
    # Test each IP for Ollama connectivity
    for ip in candidate_ips:
        endpoint = f"http://{ip}:11434"
        if test_ollama_connection(endpoint):
            logger.info(f"Found working Ollama endpoint: {endpoint}")
            return endpoint
    
    # Fallback
    fallback_endpoint = f"http://{candidate_ips[0] if candidate_ips else '172.31.160.1'}:11434"
    logger.warning(f"No working Ollama endpoint found, using fallback: {fallback_endpoint}")
    return fallback_endpoint


def test_ollama_connection(endpoint: str = None) -> bool:
    """
    Test if Ollama is accessible at the given endpoint.
    
    Args:
        endpoint: The Ollama endpoint URL. If None, would cause recursion - don't do this!
        
    Returns:
        bool: True if Ollama is accessible, False otherwise
    """
    if endpoint is None:
        logger.error("test_ollama_connection called without endpoint - this would cause recursion!")
        return False
    
    try:
        # Use urllib instead of requests (built-in module)
        import urllib.request
        import urllib.error
        
        # Test the /api/tags endpoint
        test_url = f"{endpoint}/api/tags" if not endpoint.endswith('/') else f"{endpoint}api/tags"
        
        with urllib.request.urlopen(test_url, timeout=3) as response:
            if response.status == 200:
                return True
        return False
    except Exception as e:
        logger.debug(f"Connection test failed for {endpoint}: {e}")
        return False


if __name__ == "__main__":
    # Test the utilities
    print(f"Windows host IP: {get_windows_host_ip()}")
    
    # Test Ollama endpoint detection
    endpoint = get_ollama_endpoint()
    print(f"Ollama endpoint: {endpoint}")
    
    # Test connection to the detected endpoint
    accessible = test_ollama_connection(endpoint)
    print(f"Ollama accessible: {accessible}")