# 📘 Finvista User Guide

## Table of Contents
- [Getting Started](#getting-started)
- [Dashboard Overview](#dashboard-overview)
- [Covered Warrants Analysis](#covered-warrants-analysis)
- [Credit Health Analysis](#credit-health-analysis)
- [Paper Trading](#paper-trading)
- [Market Overview](#market-overview)
- [Settings & Configuration](#settings--configuration)

---

## Getting Started

### Prerequisites
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection for live market data
- (Optional) Telegram account for alerts

### First-Time Setup

1. **Access the Application**
   - Open your browser and navigate to the Finvista URL
   - If authentication is enabled, you'll see the login page

2. **Create Account / Login**
   - For demo purposes, use the default demo account:
     - Username: `demo`
     - Password: `finvista123`
   - For production, register a new account

3. **Initial Dashboard Tour**
   - **Home Page**: Market overview with top signals
   - **CW Opportunities**: Filter and analyze covered warrants
   - **Credit Health**: Check corporate financial health
   - **Portfolio**: Manage paper trading positions
   - **Settings**: Configure preferences

---

## Dashboard Overview

### Home Page Features

**Market Brief Panel**
- Live CW market signals
- Top buy/skip recommendations
- Market sentiment indicators
- Quick access to detailed analysis

**Key Metrics**
- VN30 CW pulse
- Signal stack (G-score)
- Credit layer (Z-score)

**Feature Cards**
- CW Opportunities: Filter by score, signal, gearing
- Credit Health: Altman Z-score analysis
- Paper Trading: HOSE-compliant simulation

---

## Covered Warrants Analysis

### Understanding the Interface

**Filter Options**
- **Strategy**: Safe, Balanced, Aggressive
- **Underlying**: Filter by stock ticker
- **Score Range**: Minimum G-score threshold
- **Days to Maturity**: Time-based filter

**Key Columns**
- **Symbol**: CW ticker code
- **Underlying**: Base stock
- **Price**: Current market price
- **IV/HV**: Implied vs Historical volatility
- **Delta**: Sensitivity to underlying price
- **Theta**: Time decay rate
- **G-score**: Composite signal score
- **Signal**: BUY/SKIP recommendation

### Reading the Signals

**BUY Signal**
- High G-score (>70)
- Positive IV/HV ratio
- Delta in optimal range (0.3-0.7)
- Sufficient days to maturity (>15)

**SKIP Signal**
- Low G-score (<50)
- Excessive premium (>18%)
- Deep OTM (Delta <0.15)
- Near maturity (<10 days)

### Advanced Analysis

**Greeks Interpretation**
- **Delta**: Price sensitivity (0-1)
  - >0.7: Deep ITM, low leverage
  - 0.3-0.7: Optimal balance
  - <0.3: OTM, high leverage/high risk

- **Gamma**: Delta sensitivity
  - High gamma: Rapid delta changes
  - Low gamma: Stable delta

- **Theta**: Time decay (daily)
  - Negative: Value decreases over time
  - Higher negative: Faster decay

- **Vega**: Volatility sensitivity
  - Positive: Benefits from volatility increase

---

## Credit Health Analysis

### Corporate Financial Health

**Input**
- Enter stock ticker (e.g., VNM, FPT, HPG)

**Output Metrics**
- **Altman Z-score**: Bankruptcy prediction
  - >2.99: Safe zone
  - 1.81-2.99: Grey zone
  - <1.81: Distress zone

- **Industry-adjusted ratios**: Peer comparison
- **Merton DD**: Distance-to-default
- **Probability of default**: Risk percentage

### Using Credit Health for CW Trading

**Integration with CW Analysis**
- Credit health affects underlying stock risk
- Distressed underlying = Higher CW risk
- Combine Z-score with CW signals

**Best Practices**
- Avoid CW on distressed underlyings
- Prefer safe/grey zone companies
- Monitor credit health changes

---

## Paper Trading

### Getting Started

**Initial Setup**
- Default capital: 100,000,000 VND
- HOSE-compliant lot sizes (multiples of 100)
- T+2 settlement simulation

### Placing Orders

**Order Form**
- **Symbol**: CW ticker
- **Side**: BUY/SELL
- **Quantity**: Multiple of 100
- **Price**: Market or limit
- **Reason**: Strategy notes

**Order Validation**
- Quantity must be multiple of 100
- Sufficient cash for BUY orders
- Sufficient position for SELL orders

### Portfolio Management

**Active Positions**
- Real-time P/L calculation
- T+2.5 settlement lock
- Risk-based sell recommendations

**Risk Management**
- Automatic stop-loss at -15%
- Take-profit at +20%
- Theta decay warnings

### Transaction History

**Log Details**
- Date & time
- Symbol & type
- Quantity & price
- Fees & total value
- Strategy notes

---

## Market Overview

### Market Regime Detection

**Regime Types**
- **Bullish**: Upward trend, low volatility
- **Bearish**: Downward trend, high volatility
- **Sideways**: Range-bound, moderate volatility
- **Transition**: Regime change detected

**Indicators**
- HMM (Hidden Markov Model)
- GARCH volatility
- Kalman filter trend
- Multi-timeframe EMA

### Using Regime Information

**Trading Strategy Adjustment**
- Bullish: Focus on ITM CW, lower leverage
- Bearish: Consider OTM for hedging
- Sideways: Range trading strategies
- Transition: Reduce position sizes

---

## Settings & Configuration

### Preferences

**Theme**
- Light/Dark mode
- Color scheme (Blue, Green, Purple)

**Density**
- Compact: More data per screen
- Comfortable: Balanced spacing
- Spacious: Maximum readability

**Language**
- English
- Vietnamese

**Motion**
- Smooth: Animated transitions
- Static: Instant changes

### API Configuration

**Backend URL**
- Local: `http://127.0.0.1:8008`
- Production: Set by admin

**Data Refresh**
- Auto-refresh interval
- Manual refresh button

### Account Settings

**Profile**
- Username display
- Account creation date

**Security**
- Change password
- Session management

---

## Tips & Best Practices

### CW Trading

1. **Diversify**: Don't concentrate on single underlying
2. **Monitor Greeks**: Track delta and theta changes
3. **Respect Signals**: Follow BUY/SKIP recommendations
4. **Time Management**: Avoid near-maturity CW
5. **Credit Check**: Verify underlying health

### Risk Management

1. **Position Sizing**: Max 20% per CW
2. **Stop Loss**: Use -15% automatic stop
3. **Take Profit**: Book profits at +20%
4. **Settlement**: Account for T+2.5 lock
5. **Volatility**: Adjust for IV/HV ratio

### Market Analysis

1. **Regime Awareness**: Adapt to market conditions
2. **Credit Monitoring**: Watch for distress signals
3. **News Impact**: Consider corporate events
4. **Technical Indicators**: Use multiple timeframes
5. **Portfolio Balance**: Mix ITM/OTM positions

---

## Troubleshooting

### Common Issues

**Data Not Loading**
- Check internet connection
- Verify backend URL in settings
- Refresh page

**Orders Not Executing**
- Verify sufficient funds/positions
- Check HOSE lot size rules
- Ensure market is open

**Credit Health Unavailable**
- Ticker may not be in database
- Check ticker spelling
- Try alternative tickers

### Performance Issues

**Slow Loading**
- Reduce data refresh frequency
- Close unused browser tabs
- Check internet speed

**High Memory Usage**
- Clear browser cache
- Restart browser
- Close other applications

---

## Support & Resources

### Documentation
- API Documentation: `/docs` endpoint
- Technical Guide: See repository
- Deployment Guide: `DEPLOYMENT_GUIDE.md`

### Contact
- GitHub Issues: Report bugs
- Email: Support contact (if configured)
- Community: Forum/Discord (if available)

### Updates
- Check release notes for new features
- Follow project roadmap
- Subscribe to updates (if available)

---

## Glossary

**CW**: Covered Warrant - Derivative security
**ITM**: In-The-Money - Profitable if exercised
**OTM**: Out-Of-The-Money - Not profitable if exercised
**IV**: Implied Volatility - Market's expected volatility
**HV**: Historical Volatility - Past price volatility
**Greeks**: Risk measures (Delta, Gamma, Theta, Vega)
**Z-score**: Credit health metric
**G-score**: Composite CW signal score
**T+2**: Settlement period (2 business days)
**HOSE**: Ho Chi Minh Stock Exchange
