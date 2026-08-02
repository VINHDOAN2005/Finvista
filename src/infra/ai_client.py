# -*- coding: utf-8 -*-
"""
🤖 FINVISTA: AI CLIENT UTILITY
================================
Unified AI client for Gemini integration using gemini-web2api.
Supports both free web API and official Google AI API.

Author: samvo
"""

import os
import subprocess
import socket
import time
import sys
from typing import Optional, List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Sanitize proxy variables to prevent httpx IPv6 loopback crash (::1)
for var in ["no_proxy", "NO_PROXY"]:
    if var in os.environ:
        parts = [p.strip() for p in os.environ[var].split(",")]
        cleaned = [p for p in parts if "::1" not in p]
        os.environ[var] = ",".join(cleaned)

load_dotenv()

class AIClient:
    """Unified AI client for Gemini integration."""
    
    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        # Prioritize OpenRouter if API key is present and configured
        if self.openrouter_api_key and not self.openrouter_api_key.startswith("YOUR_") and "sk-or-v1" in self.openrouter_api_key:
            self.use_web_api = False
            self.base_url = "https://openrouter.ai/api/v1"
            self.default_model = "google/gemini-2.5-flash"
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.openrouter_api_key
            )
            print("AIClient: Connected via OpenRouter API Gateway.")
        else:
            self.use_web_api = True
            self.base_url = "http://localhost:8081/v1"
            self.default_model = "gemini-3.5-flash"
            self._ensure_proxy_running()
            self.client = OpenAI(
                base_url=self.base_url,
                api_key="sk-web-api"
            )
            print("AIClient: Connected via local Web-to-API Proxy.")
    
    def _is_port_open(self, port: int) -> bool:
        """Check if a local port is already open."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def _ensure_proxy_running(self):
        """Automatically starts the gemini_web2api proxy if not running."""
        if self._is_port_open(8081):
            return # Already running
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        proxy_script = os.path.join(base_dir, "scripts", "maintenance", "gemini_web2api.py")
        if not os.path.exists(proxy_script):
            print(f"Warning: AI Proxy script not found at {proxy_script}")
            return

        print("Starting Gemini AI Proxy automatically...")
        try:
            # Launch the proxy in the background
            # We use subprocess.Popen to let it run independently
            subprocess.Popen(
                [sys.executable, proxy_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            # Give it a few seconds to warm up
            time.sleep(2)
            if self._is_port_open(8081):
                print("Gemini AI Proxy started successfully.")
            else:
                print("Warning: Gemini AI Proxy is taking longer than expected to start.")
        except Exception as e:
            print(f"Error: Failed to start AI Proxy: {e}")
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        try:
            max_tokens = kwargs.get("max_tokens") or 2048
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                max_tokens=max_tokens,
                timeout=30.0
            )
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            try:
                if "Connection error" in error_msg or "ConnectError" in error_msg:
                    print("AI Client Connection Error: Unable to reach local proxy.")
                else:
                    print(f"AI Client Error: {error_msg}")
            except Exception:
                pass
            return ""
    
    def _generate_rule_based_financial_commentary(self, ticker: str, **kwargs) -> str:
        return f"{ticker} đối mặt với rủi ro tài chính do các chỉ số thanh khoản và nợ vay suy yếu."

    def generate_financial_commentary(self, ticker: str, **kwargs) -> str:
        response = self.chat([{"role": "user", "content": f"Phân tích {ticker}"}])
        if not response:
            return self._generate_rule_based_financial_commentary(ticker)
        return response
    
    def generate_trading_signal_commentary(self, cw_code: str, signal: str, **kwargs) -> str:
        return f"Tín hiệu {signal} cho {cw_code}. Cần theo dõi thêm."

    def analyze_chart_vision(self, **kwargs) -> str:
        return "Vision analysis requires API connection."

_ai_client: Optional[AIClient] = None

def get_ai_client() -> AIClient:
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client
