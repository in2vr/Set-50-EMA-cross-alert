import os
import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime

# ==========================================
# ⚙️ ส่วนตั้งค่า (ดึงจาก GitHub Secrets)
# ==========================================
# ดึงค่าจาก Secret ที่ตั้งไว้ใน GitHub
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# รายชื่อหุ้น SET50 (ข้อมูลล่าสุด)
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
    """ส่งข้อความแจ้งเตือนผ่าน Telegram Bot พร้อมตรวจสอบความถูกต้อง"""
    # ตรวจสอบว่ามี Token และ Chat ID หรือไม่
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Error: ไม่พบ TELEGRAM_BOT_TOKEN ใน Secrets (กรุณาตั้งค่าใน GitHub Settings)")
        return
    if not TELEGRAM_CHAT_ID:
        print("❌ Error: ไม่พบ TELEGRAM_CHAT_ID ใน Secrets (กรุณาตั้งค่าใน GitHub Settings)")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        # พยายามส่งข้อความ
        response = requests.post(url, json=payload, timeout=10)
        
        # ตรวจสอบผลลัพธ์จาก Telegram
        if response.status_code == 200:
            print("✅ ส่งข้อความ Telegram สำเร็จ")
        else:
            print(f"❌ ส่ง Telegram ไม่ผ่าน (Status {response.status_code}): {response.text}")
            
    except Exception as e:
        print(f"❌ Error sending Telegram: {e}")

def analyze_stock(symbol):
    """วิเคราะห์หุ้นรายตัว"""
    try:
        # ดึงข้อมูลย้อนหลัง
        df = yf.download(symbol, period='6mo', interval='1d', progress=False)
        
        # ถ้าข้อมูลน้อยเกินไป ให้ข้าม
        if len(df) < 26: 
            return None 

        # คำนวณ EMA
        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()

        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        
        # ใช้ชื่อหุ้นแบบไม่มี .BK เพื่อความสวยงาม
        stock_name = symbol.replace('.BK', '')
        
        # 1. เช็ค Golden Cross (ตัดขึ้น)
        if yesterday['EMA12'] < yesterday['EMA26'] and today['EMA12'] > today['EMA26']:
            return f"🟢 *{stock_name}* : ตัดขึ้น (Buy)\n`EMA12 > EMA26`"
        
        # 2. เช็ค Dead Cross (ตัดลง)
        elif yesterday['EMA12'] > yesterday['EMA26'] and today['EMA12'] < today['EMA26']:
            return f"🔴 *{stock_name}* : ตัดลง (Sell)\n`EMA12 < EMA26`"

        # 3. เช็ค Converging (กำลังจะตัด)
        else:
            diff = abs(today['EMA12'] - today['EMA26']) / today['Close'] * 100
            # ถ้าระยะห่างน้อยกว่า 0.3%
            if diff < 0.3:
                trend = "จะตัดขึ้น" if today['EMA12'] < today['EMA26'] else "จะตัดลง"
                return f"⚠️ *{stock_name}* : กำลังบีบตัว ({trend})\n`Gap: {diff:.2f}%`"
        
        return None
        
    except Exception as e:
        # ถ้า Error ให้ข้ามไปเงียบๆ (ไม่ให้โปรแกรมพัง)
        return None

def main():
    print("⏳ เริ่มสแกนหุ้น SET50...")
    
    # เช็ค Debug เพื่อดูว่า Token เข้ามาในระบบไหม
    if TELEGRAM_BOT_TOKEN:
        print(f"🔑 พบ Token: ...{TELEGRAM_BOT_TOKEN[-5:]} (ซ่อนเพื่อความปลอดภัย)")
    else:
        print("⛔️ ไม่พบ TELEGRAM_BOT_TOKEN! โปรดตรวจสอบ Secrets")

    found_signals = []
    
    # วนลูปเช็คหุ้น
    for i, symbol in enumerate(SET50_SYMBOLS):
        # print(f"Checking {symbol}...", end='\r') # บรรทัดนี้บางทีทำให้ log ใน GitHub ดูยาก
        print(f"[{i+1}/{len(SET50_SYMBOLS)}] กำลังตรวจสอบ: {symbol}")
        
        result = analyze_stock(symbol)
        if result: 
            found_signals.append(result)
    
    print("\n✅ สแกนเสร็จสิ้น!")

    # ส่งผลลัพธ์
    if found_signals:
        header = f"📊 *SET50 EMA Cross Update*\n📅 {datetime.now().strftime('%d/%m/%Y')}\n{'='*20}\n"
        msg = header + "\n\n".join(found_signals)
        send_telegram_msg(msg)
    else:
        print("วันนี้ไม่พบหุ้นที่เข้าเงื่อนไข")
        # บังคับส่งข้อความแจ้งเตือน เพื่อทดสอบว่าบอททำงานจริง
        send_telegram_msg("✅ บอททำงานเสร็จแล้วครับ แต่วันนี้ไม่มีหุ้นเข้าเงื่อนไข")

if __name__ == "__main__":
    main()
