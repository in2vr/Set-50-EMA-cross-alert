import os
import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime

# ==========================================
# ⚙️ ส่วนตั้งค่า (CONFIGURATION)
# ==========================================

# 1. ใส่ Token ที่ได้จาก @BotFather
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# 2. ใส่ Chat ID ของคุณ (เป็นตัวเลข) ที่ได้จาก @userinfobot
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# รายชื่อหุ้น SET50 (อัปเดตข้อมูลล่าสุด)
SET50_SYMBOLS = [
    'ADVANC.BK', 'AOT.BK', 'AWC.BK', 'BANPU.BK', 'BBL.BK', 'BDMS.BK', 'BEM.BK', 'BGRIM.BK',
    'BH.BK', 'BJC.BK', 'BTS.BK', 'CBG.BK', 'CENTEL.BK', 'COM7.BK', 'CPALL.BK', 'CPF.BK',
    'CPN.BK', 'CRC.BK', 'DELTA.BK', 'EA.BK', 'EGCO.BK', 'GLOBAL.BK', 'GPSC.BK', 'GULF.BK',
    'HMPRO.BK', 'INTUCH.BK', 'IVL.BK', 'KBANK.BK', 'KCE.BK', 'KTB.BK', 'KTC.BK', 'LH.BK',
    'MINT.BK', 'MTC.BK', 'OR.BK', 'OSP.BK', 'PTT.BK', 'PTTEP.BK', 'PTTGC.BK', 'RATCH.BK',
    'SAWAD.BK', 'SCB.BK', 'SCC.BK', 'SCGP.BK', 'TISCO.BK', 'TOP.BK', 'TRUE.BK', 'TTB.BK',
    'TU.BK', 'WHA.BK'
]

# ==========================================
# 🚀 ฟังก์ชันการทำงาน
# ==========================================

def send_telegram_msg(message):
    """ส่งข้อความแจ้งเตือนผ่าน Telegram Bot"""
    url = f"https://api.telegram.org/bot{AAEp8gilewNXgttpxOcgobP02HQMskfLIHgOKEN}/sendMessage"
    payload = {
        'chat_id': 8476445868,
        'text': message,
        'parse_mode': 'Markdown' # จัดรูปแบบข้อความได้ (ตัวหนา/ตัวเอียง)
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"❌ ส่ง Telegram ไม่ผ่าน: {response.text}")
    except Exception as e:
        print(f"❌ Error sending Telegram: {e}")

def analyze_stock(symbol):
    """คำนวณ EMA 12/26 และหาจุดตัด"""
    try:
        # ดึงข้อมูลย้อนหลัง 6 เดือน
        df = yf.download(symbol, period='6mo', interval='1d', progress=False)
        
        if len(df) < 26:
            return None 

        # คำนวณ EMA
        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()

        today = df.iloc[-1]
        yesterday = df.iloc[-2]

        signal_msg = ""
        stock_name = symbol.replace('.BK', '')
        
        # --- เงื่อนไขการแจ้งเตือน ---

        # 1. Golden Cross (ตัดขึ้น)
        if yesterday['EMA12'] < yesterday['EMA26'] and today['EMA12'] > today['EMA26']:
            signal_msg = f"🟢 *{stock_name}* : ตัดขึ้น (Buy Signal)\n`EMA12 ตัด EMA26 ขึ้นด้านบน`"
        
        # 2. Dead Cross (ตัดลง)
        elif yesterday['EMA12'] > yesterday['EMA26'] and today['EMA12'] < today['EMA26']:
            signal_msg = f"🔴 *{stock_name}* : ตัดลง (Sell Signal)\n`EMA12 ตัด EMA26 ลงด้านล่าง`"

        # 3. กำลังบีบตัว (Converging)
        else:
            diff_percent = abs(today['EMA12'] - today['EMA26']) / today['Close'] * 100
            if diff_percent < 0.3: # ปรับให้แคบลงเหลือ 0.3% เพื่อความแม่นยำ
                trend = "แนวโน้มจะตัดขึ้น" if today['EMA12'] < today['EMA26'] else "แนวโน้มจะตัดลง"
                signal_msg = f"⚠️ *{stock_name}* : กำลังบีบตัว ({trend})\n`เส้น EMA ใกล้กันมาก ({diff_percent:.2f}%)`"

        return signal_msg

    except Exception as e:
        return None

def main():
    print("⏳ เริ่มสแกนหุ้น SET50...")
    found_signals = []
    
    # วนลูปเช็คหุ้นทุกตัว
    for i, symbol in enumerate(SET50_SYMBOLS):
        print(f"({i+1}/{len(SET50_SYMBOLS)}) Checking {symbol}...", end='\r')
        result = analyze_stock(symbol)
        if result:
            found_signals.append(result)
    
    print("\n✅ สแกนเสร็จสิ้น!")

    # สรุปผลและส่งข้อความ
    if found_signals:
        header = f"📊 *สรุป SET50 EMA 12/26 Cross*\n📅 วันที่: {datetime.now().strftime('%d/%m/%Y')}\n{'='*25}\n"
        
        # Telegram มีลิมิตความยาวข้อความ หากยาวเกินต้องแบ่งส่ง
        message_chunk = header
        for signal in found_signals:
            if len(message_chunk) + len(signal) > 4000: # Telegram limit ประมาณ 4096 chars
                send_telegram_msg(message_chunk)
                message_chunk = ""
            message_chunk += signal + "\n\n"
            
        if message_chunk:
            send_telegram_msg(message_chunk)
            print("📩 ส่งแจ้งเตือนไปยัง Telegram แล้ว")
    else:
        print("วันนี้ไม่พบหุ้นที่เข้าเงื่อนไข")
        send_telegram_msg("✅ สแกนเสร็จสิ้นแล้ว แต่วันนี้ไม่มีหุ้นที่เข้าเงื่อนไขครับ")

if __name__ == "__main__":

    main()
