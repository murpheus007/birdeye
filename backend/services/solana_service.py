"""
Solana service for RPC interactions
"""
import os
import aiohttp
from typing import Dict, Any, Optional


class SolanaService:
    """Service for interacting with Solana blockchain"""
    
    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or os.getenv('SOLANA_RPC_URL')
    
    async def get_token_info(self, mint: str) -> Dict[str, Any]:
        """Get token information from Solana"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rpc_url,
                    json={
                        'jsonrpc': '2.0',
                        'id': 1,
                        'method': 'getTokenSupply',
                        'params': [mint],
                    }
                ) as response:
                    data = await response.json()
                    return data
        except Exception as e:
            print(f"Error fetching token info: {e}")
            return {}
    
    async def get_account_info(self, address: str) -> Dict[str, Any]:
        """Get account information"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rpc_url,
                    json={
                        'jsonrpc': '2.0',
                        'id': 1,
                        'method': 'getAccountInfo',
                        'params': [address],
                    }
                ) as response:
                    data = await response.json()
                    return data
        except Exception as e:
            print(f"Error fetching account info: {e}")
            return {}
