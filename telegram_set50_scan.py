import os
import pandas as pd
import requests
import time
from datetime import datetime
from tvDatafeed import TvDatafeed, Interval

# ==========================================
# ⚙️ ส่วนตั้งค่า
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# รายชื่อหุ้น SET50 (ไม่ต้องมี .BK แล้ว เพราะ TradingView ใช้ชื่อเพียวๆ)
SET50_SYMBOLS = [
    'ADVANC', 'AOT', 'AWC', 'BANPU', 'BBL', 'BDMS', 'BEM', 'BGRIM',
    'BH', 'BJC', 'BTS', 'CBG', 'CENTEL', 'COM7', 'CPALL', 'CPF',
    'CPN', 'CRC', 'DELTA', 'EA', 'EGCO', 'GLOBAL', 'GPSC', 'GULF',
    'HMPRO', 'INTUCH', 'IVL', 'KBANK', 'KCE', 'KTB', 'KTC', 'LH',
    'MINT', 'MTC', 'OR', 'OSP', 'PTT', 'PTTEP', 'PTTGC', 'RATCH',
    'SAWAD', 'SCB', 'SCC', 'SCGP', 'TISCO', 'TOP', 'TRUE', 'TTB',
    'TU', 'WHA'
]

# ==========================================
# 🚀 ฟังก์ชันการทำงาน
# ==========================================

def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Error: ไม่พบ Token หรือ Chat ID")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Error sending Telegram: {e}")

def analyze_stock(tv, symbol):
    """วิเคราะห์หุ้นโดยใช้ข้อมูลจาก TradingView"""
    try:
        # ดึงข้อมูลจาก TradingView (ตลาด SET)
        df = tv.get_hist(symbol=symbol, exchange='SET', interval=Interval.in_daily, n_bars=100)
        
        if df is None or len(df) < 26:
            return None

        # คำนวณ EMA (สูตรเดียวกับ TradingView)
        df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()

        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        
        # ตรวจสอบวันที่ของข้อมูลล่าสุด (Debug)
        last_date = df.index[-1].strftime('%Y-%m-%d')
        # print(f"Checking {symbol} ({last_date})... EMA12: {today['EMA12']:.2f}, EMA26: {today['EMA26']:.2f}")

        # 1. Golden Cross (ตัดขึ้น)
        if yesterday['EMA12'] < yesterday['EMA26'] and today['EMA12'] > today['EMA26']:
            return f"🟢 *{symbol}* ({last_date}): ตัดขึ้น (Buy)\n`EMA12 ({today['EMA12']:.2f}) > EMA26 ({today['EMA26']:.2f})`"
        
        # 2. Dead Cross (ตัดลง)
        elif yesterday['EMA12'] > yesterday['EMA26'] and today['EMA12'] < today['EMA26']:
            return f"🔴 *{symbol}* ({last_date}): ตัดลง (Sell)\n`EMA12 ({today['EMA12']:.2f}) < EMA26 ({today['EMA26']:.2f})`"

        # 3. Converging (ใกล้ตัด) gap < 0.3%
        else:
            diff = abs(today['EMA12'] - today['EMA26']) / today['close'] * 100
            if diff < 0.3:
                trend = "จะตัดขึ้น" if today['EMA12'] < today['EMA26'] else "จะตัดลง"
                return f"⚠️ *{symbol}* ({last_date}): กำลังบีบตัว ({trend})\n`Gap: {diff:.2f}%`"
        
        return None

    except Exception as e:
        # print(f"Error analyzing {symbol}: {e}")
        return None

def main():
    print("⏳ เริ่มสแกนหุ้นจาก TradingView Data...")
    
    # เริ่มต้นระบบ TradingView (แบบไม่ Login)
    tv = TvDatafeed()
    
    found_signals = []
    
    for i, symbol in enumerate(SET50_SYMBOLS):
        print(f"[{i+1}/{len(SET50_SYMBOLS)}] Checking {symbol}...", end='\r')
        result = analyze_stock(tv, symbol)
        if result: 
            found_signals.append(result)
    
    print("\n✅ สแกนเสร็จสิ้น!")

    if found_signals:
        header = f"📊 *SET50 (TradingView Source)*\n📅 {datetime.now().strftime('%d/%m/%Y')}\n{'='*20}\n"
        msg = header + "\n\n".join(found_signals)
        send_telegram_msg(msg)
    else:
        print("วันนี้ไม่พบหุ้นที่เข้าเงื่อนไข")
        send_telegram_msg("✅ สแกนเสร็จแล้ว (Source: TradingView) ไม่พบหุ้นเข้าเงื่อนไข")

if __name__ == "__main__":
    main()
