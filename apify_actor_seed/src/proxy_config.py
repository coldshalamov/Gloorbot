"""
Proxy Provider Configurations for Optimized Lowe's Scraper

This file contains configuration for different residential proxy providers.
Choose based on your budget vs quality requirements.
"""

import os
from typing import Optional


class ProxyConfig:
    """Base proxy configuration."""
    
    def get_proxy_url(self, session_id: str) -> str:
        """Generate proxy URL with session locking."""
        raise NotImplementedError


class BrightDataProxy(ProxyConfig):
    """
    Bright Data (formerly Luminati)
    
    Cost: $15/GB
    Quality: ⭐⭐⭐⭐⭐ Premium
    Block Rate: <1%
    
    Best for: Production, high-value scraping
    """
    
    def __init__(self):
        self.host = "brd.superproxy.io"
        self.port = 22225
        self.username = os.getenv("BRIGHT_DATA_USERNAME")
        self.password = os.getenv("BRIGHT_DATA_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError("BRIGHT_DATA_USERNAME and BRIGHT_DATA_PASSWORD must be set")
    
    def get_proxy_url(self, session_id: str) -> str:
        # Bright Data session format: username-session-SESSIONID
        username_with_session = f"{self.username}-session-{session_id}"
        return f"http://{username_with_session}:{self.password}@{self.host}:{self.port}"


class SmartproxyProxy(ProxyConfig):
    """
    Smartproxy
    
    Cost: $12.5/GB
    Quality: ⭐⭐⭐⭐ Good
    Block Rate: 1-2%
    
    Best for: Balanced cost/quality
    """
    
    def __init__(self):
        self.host = "gate.smartproxy.com"
        self.port = 7000
        self.username = os.getenv("SMARTPROXY_USERNAME")
        self.password = os.getenv("SMARTPROXY_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError("SMARTPROXY_USERNAME and SMARTPROXY_PASSWORD must be set")
    
    def get_proxy_url(self, session_id: str) -> str:
        # Smartproxy session format: user-USERNAME-session-SESSIONID
        username_with_session = f"user-{self.username}-session-{session_id}"
        return f"http://{username_with_session}:{self.password}@{self.host}:{self.port}"


class ProxyCheapProxy(ProxyConfig):
    """
    Proxy-Cheap
    
    Cost: $5/GB
    Quality: ⭐⭐⭐ Acceptable
    Block Rate: 5-10%
    
    Best for: Budget scraping, testing
    """
    
    def __init__(self):
        self.host = "residential.proxy-cheap.com"
        self.port = 10001
        self.username = os.getenv("PROXYCHEAP_USERNAME")
        self.password = os.getenv("PROXYCHEAP_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError("PROXYCHEAP_USERNAME and PROXYCHEAP_PASSWORD must be set")
    
    def get_proxy_url(self, session_id: str) -> str:
        # Proxy-Cheap session format: username-session-SESSIONID
        username_with_session = f"{self.username}-session-{session_id}"
        return f"http://{username_with_session}:{self.password}@{self.host}:{self.port}"


class OxylabsProxy(ProxyConfig):
    """
    Oxylabs
    
    Cost: $10/GB (enterprise pricing)
    Quality: ⭐⭐⭐⭐⭐ Premium
    Block Rate: <1%
    
    Best for: Enterprise, requires account manager
    """
    
    def __init__(self):
        self.host = "pr.oxylabs.io"
        self.port = 7777
        self.username = os.getenv("OXYLABS_USERNAME")
        self.password = os.getenv("OXYLABS_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError("OXYLABS_USERNAME and OXYLABS_PASSWORD must be set")
    
    def get_proxy_url(self, session_id: str) -> str:
        # Oxylabs session format: customer-USERNAME-session-SESSIONID
        username_with_session = f"customer-{self.username}-session-{session_id}"
        return f"http://{username_with_session}:{self.password}@{self.host}:{self.port}"


class IPRoyalProxy(ProxyConfig):
    """
    IPRoyal
    
    Cost: $7/GB
    Quality: ⭐⭐⭐⭐ Good
    Block Rate: 2-3%
    
    Best for: Mid-range budget
    """
    
    def __init__(self):
        self.host = "geo.iproyal.com"
        self.port = 12321
        self.username = os.getenv("IPROYAL_USERNAME")
        self.password = os.getenv("IPROYAL_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError("IPROYAL_USERNAME and IPROYAL_PASSWORD must be set")
    
    def get_proxy_url(self, session_id: str) -> str:
        # IPRoyal session format: USERNAME_session-SESSIONID
        username_with_session = f"{self.username}_session-{session_id}"
        return f"http://{username_with_session}:{self.password}@{self.host}:{self.port}"


def get_proxy_provider(provider_name: str = "proxy-cheap") -> ProxyConfig:
    """
    Factory function to get proxy provider.
    
    Args:
        provider_name: One of: bright-data, smartproxy, proxy-cheap, oxylabs, iproyal
    
    Returns:
        ProxyConfig instance
    
    Example:
        proxy = get_proxy_provider("proxy-cheap")
        url = proxy.get_proxy_url("store_1234")
    """
    providers = {
        "bright-data": BrightDataProxy,
        "smartproxy": SmartproxyProxy,
        "proxy-cheap": ProxyCheapProxy,
        "oxylabs": OxylabsProxy,
        "iproyal": IPRoyalProxy,
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}. Choose from: {list(providers.keys())}")
    
    return providers[provider_name]()


# Usage in main_optimized.py:
"""
# At the top of main_optimized.py, replace proxy configuration:

from proxy_config import get_proxy_provider

# In BrowserPool.__init__:
self.proxy_provider = get_proxy_provider(os.getenv("PROXY_PROVIDER", "proxy-cheap"))

# In get_or_create_browser:
proxy_url = self.proxy_provider.get_proxy_url(f"store_{store_id}")
launch_options["proxy"] = {"server": proxy_url}
"""
