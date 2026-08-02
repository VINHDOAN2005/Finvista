# -*- coding: utf-8 -*-
"""
🚀 FINVISTA TELEGRAM WEBHOOK SERVER
====================================
Flask server to handle Telegram webhook callbacks for inline keyboard buttons.
"""

from flask import Flask, request, jsonify
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infra.telegram_alerts import handle_callback_query

app = Flask(__name__)

@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """Handle incoming webhook updates from Telegram"""
    try:
        data = request.get_json()
        
        # Check if this is a callback query (button click)
        if 'callback_query' in data:
            callback_query = data['callback_query']
            callback_query_id = callback_query['id']
            callback_data = callback_query.get('data', '')
            from_user = callback_query.get('from', {})
            chat_id = from_user.get('id', '')
            
            print(f"📥 Received callback: {callback_data} from user {chat_id}")
            
            # Handle the callback
            handle_callback_query(callback_query_id, callback_data, str(chat_id))
            
            return jsonify({'status': 'ok'})
        
        # Handle regular messages (if needed)
        if 'message' in data:
            message = data['message']
            chat_id = message.get('chat', {}).get('id', '')
            text = message.get('text', '')
            
            print(f"📩 Received message: {text} from chat {chat_id}")
            
            # You can add command handling here if needed
            # For example: /start, /help, /status, etc.
            
            return jsonify({'status': 'ok'})
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        print(f"❌ Error handling webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'finvista-telegram-webhook'})

if __name__ == '__main__':
    port = int(os.getenv('WEBHOOK_PORT', 5000))
    print(f"🚀 Starting Telegram webhook server on port {port}...")
    print(f"📡 Webhook endpoint: http://localhost:{port}/webhook/telegram")
    app.run(host='0.0.0.0', port=port, debug=True)
