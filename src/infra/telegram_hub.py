# -*- coding: utf-8 -*-
"""
🛡️ FINVISTA: TELEGRAM ALERT HUB (Stateful Controller)
=====================================================
Centralized hub to control alert fatigue, deduplicate signals, 
and manage notification throttling.

Key Features:
- Signal Persistence: Tracks what has already been sent to prevent spam.
- Smart Throttling: Only re-alerts if score increases significantly (> 5%).
- Priority Tiers: Filters noise based on user preference.
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Path for state tracking
STATE_FILE = os.path.join("data", "config", "telegram_hub_state.json")

class TelegramHub:
    def __init__(self, expiry_hours: int = 4, score_threshold_pct: float = 5.0):
        self.state_file = STATE_FILE
        self.expiry_hours = expiry_hours
        self.score_threshold_pct = score_threshold_pct
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_state(self):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            print(f"⚠️ TelegramHub: Failed to save state: {e}")

    def filter_signals(self, signals: List[Dict[str, Any]], signal_type: str = "CW_OPPORTUNITY") -> List[Dict[str, Any]]:
        """
        Filters out redundant signals.
        Returns only 'fresh' or 'significantly improved' signals.
        """
        now = datetime.now()
        filtered = []
        
        # Clean up old states first
        self._cleanup_expired(now)

        for sig in signals:
            # Generate a unique key based on type and symbol
            symbol = sig.get('A_MaCW') or sig.get('ticker') or sig.get('symbol')
            if not symbol: continue
            
            key = f"{signal_type}:{symbol}"
            current_score = float(sig.get('G_Score', sig.get('score', 0)))
            
            # Logic:
            # 1. If key doesn't exist -> Send (New signal)
            # 2. If exists but expired -> Send (Re-alert)
            # 3. If exists and NOT expired:
            #    - Only send if score improved significantly (> score_threshold_pct)
            
            prev_data = self.state.get(key)
            
            should_send = False
            if not prev_data:
                should_send = True
            else:
                last_score = prev_data.get('score', 0)
                # Improvement check: (New - Old) / Old
                improvement = 0
                if last_score > 0:
                    improvement = (current_score - last_score) / last_score * 100
                
                if improvement >= self.score_threshold_pct:
                    should_send = True
                
                # Special case: Signal upgrade (e.g., BUY -> STRONG BUY)
                if sig.get('U_Signal') != prev_data.get('signal'):
                    # Only upgrade if it gets better
                    if sig.get('U_Signal') in ['STRONG BUY', 'VOL ARBITRAGE BUY']:
                        should_send = True

            if should_send:
                filtered.append(sig)
                # Update state
                self.state[key] = {
                    'timestamp': now.isoformat(),
                    'score': current_score,
                    'signal': sig.get('U_Signal', 'ALERT'),
                    'count': prev_data.get('count', 0) + 1 if prev_data else 1
                }

        if filtered:
            self._save_state()
            
        return filtered

    def _cleanup_expired(self, now: datetime):
        """Remove state entries that are older than expiry_hours."""
        keys_to_delete = []
        cutoff = now - timedelta(hours=self.expiry_hours)
        
        for key, data in self.state.items():
            ts = datetime.fromisoformat(data['timestamp'])
            if ts < cutoff:
                keys_to_delete.append(key)
        
        for k in keys_to_delete:
            del self.state[k]

# Singleton instance for the whole project
hub = TelegramHub()

def dispatch_filtered_alerts(all_opportunities: List[Dict[str, Any]], near_expiry: List[Dict[str, Any]]):
    """
    Main entry point for the Hub. Filters and dispatches only relevant alerts.
    """
    from src.infra.telegram_alerts import send_telegram_alert_batch, load_telegram_config
    
    # 1. Filter opportunities through the smart hub
    filtered_opps = hub.filter_signals(all_opportunities, "CW_OPPORTUNITY")
    
    # 2. Filter expiry warnings (only warn once every 24h per symbol)
    expiry_hub = TelegramHub(expiry_hours=24) 
    filtered_expiry = expiry_hub.filter_signals(near_expiry, "EXPIRY_WARNING")
    
    # 3. Send if anything is left
    if filtered_opps or filtered_expiry:
        send_telegram_alert_batch(filtered_opps, filtered_expiry)
    else:
        # Check if we should log silence
        config = load_telegram_config()
        if config.get("enable_alerts"):
            print(f"🤫 [Telegram Hub] {len(all_opportunities)} signals suppressed (No significant changes).")
