# Telegram Webhook Setup Guide

## Overview
This guide explains how to set up the Telegram webhook for handling inline keyboard button callbacks in the Finvista system.

## Prerequisites

1. **Telegram Bot Token** - Already configured in `data/config/telegram_config.json` or `.env`
2. **Public URL** - Your webhook endpoint must be accessible from the internet
   - Options: ngrok, VPS, cloud hosting (AWS, GCP, Azure), etc.
3. **Flask** - Install via: `pip install Flask>=3.0.0`

## Setup Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Webhook Server

**Development (using ngrok):**
```bash
# Install ngrok from https://ngrok.com/
# Start ngrok
ngrok http 5000

# In another terminal, start the webhook server
python src/common/telegram_webhook.py
```

**Production (using VPS/Cloud):**
```bash
# Set environment variable for port (default: 5000)
export WEBHOOK_PORT=5000

# Start the webhook server
python src/common/telegram_webhook.py
```

### 3. Set Up the Webhook URL

Replace `YOUR_PUBLIC_URL` with your actual public URL (e.g., ngrok URL or domain):

```bash
python scripts/setup_telegram_webhook.py --set https://YOUR_PUBLIC_URL/webhook/telegram
```

Example with ngrok:
```bash
python scripts/setup_telegram_webhook.py --set https://abc123.ngrok.io/webhook/telegram
```

### 4. Verify Webhook Setup

```bash
python scripts/setup_telegram_webhook.py --info
```

### 5. Test the Buttons

Send a test alert to Telegram and click the buttons. The webhook server should log the callback and execute the corresponding action.

## Webhook Actions

The following button actions are implemented:

### Warrant Alerts:
- **📊 Xem CSV chi tiết** (`view_csv`) - Sends the CSV file from `data/processed/cleaned_financials.csv`
- **📥 Tải báo cáo** (`download_report`) - Sends the Excel report from `data/processed/excel_cw_report.csv`
- **⚙️ Cài đặt** (`settings`) - Not yet implemented
- **🔄 Quét lại** (`rescan`) - Triggers market rescan via `scripts/run_cw.py --all`

### Credit Distress Alerts:
- **📋 Xem danh sách đầy đủ** (`view_full_list`) - Sends the full dataset from `data/processed/final_processed_dataset.csv`
- **📥 Tải báo cáo rủi ro** (`download_risk_report`) - Sends the risk report from `data/processed/data_quality_report.json`
- **🔄 Quét lại ngay** (`rescan_credit`) - Triggers credit pipeline rescan via `run.py credit`
- **⚙️ Cài đặt cảnh báo** (`alert_settings`) - Not yet implemented

## Troubleshooting

### Webhook Not Receiving Callbacks
1. Check webhook info: `python scripts/setup_telegram_webhook.py --info`
2. Verify your public URL is accessible
3. Check webhook server logs for errors
4. Ensure Telegram bot token is correct

### Buttons Not Working
1. Verify webhook is set up correctly
2. Check webhook server is running
3. Review server logs for callback errors
4. Ensure file paths in callback actions exist

### Delete Webhook (Switch to Polling)
```bash
python scripts/setup_telegram_webhook.py --delete
```

## Production Deployment

For production, consider using:
- **Gunicorn** or **uWSGI** as WSGI server
- **Nginx** as reverse proxy
- **SSL/TLS** certificate (Let's Encrypt)
- **Systemd** service for auto-restart

Example Gunicorn command:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 src.infra.telegram_webhook:app
```

## Security Considerations

1. **Validate requests** - Consider implementing request validation
2. **Rate limiting** - Add rate limiting to prevent abuse
3. **Authentication** - Consider adding authentication to webhook endpoint
4. **HTTPS** - Always use HTTPS in production
5. **Secret token** - Telegram supports secret tokens for webhook validation

## Monitoring

The webhook server includes a health check endpoint:
```
GET /health
```

Returns: `{"status": "healthy", "service": "finvista-telegram-webhook"}`
