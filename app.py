import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import qrcode
from io import BytesIO
import hashlib

# --- KURUMSAL TEMA VE GÜVENLİK ---
st.set_page_config(page_title="Core Tarım Enterprise", layout="wide")

# Kullanıcı Giriş Sistemi (Şifreleme)
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

# CSS Tasarımı
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .sidebar .sidebar-content { background: #01204E; }
    .stMetric { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .stButton>button { border-radius: 20px; font-weight: bold; transition: 0.3s; }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı Mimarisi (Gelişmiş İlişkisel Yapı)
conn = sqlite3.connect('core_enterprise_v8.db', check_same_thread=False)
c = conn.cursor()

def db_setup():
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS hammaddeler (id INTEGER PRIMARY KEY, ad TEXT, miktar REAL, birim TEXT, kritik_seviye REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS receteler (id INTEGER PRIMARY KEY, urun_id INTEGER, hammadde_id INTEGER, miktar REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY, ad TEXT, kategori TEXT, paketleme TEXT, stok_adet INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS is_emirleri (id INTEGER PRIMARY KEY AUTOINCREMENT, no TEXT, urun_id INTEGER, hedef INTEGER, durum TEXT, kalite_onay TEXT DEFAULT "Bekliyor")')
    c.execute('CREATE TABLE IF NOT EXISTS stok_lotlari (id INTEGER PRIMARY KEY AUTOINCREMENT, urun_id INTEGER, miktar INTEGER, tett DATE, lot_no TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finans (id INTEGER PRIMARY KEY, tarih DATE, tip TEXT, miktar REAL, kategori TEXT)')
    # Varsayılan yönetici ekle
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', ?, 'Yönetici')", (make_hashes('core123'),))
    conn.commit()

db_setup()

# --- GİRİŞ EKRANI ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Core Tarım ERP Girişi")
    user = st.text_input("Kullanıcı Adı")
    pw = st.text_input("Şifre", type='password')
    if st.button("Giriş Yap"):
        c.execute("SELECT password, role FROM users WHERE username = ?", (user,))
        data = c.fetchone()
        if data and check_hashes(pw, data[0]):
            st.session_state['logged_in'] = True
            st.session_state['user'] = user
            st.session_state['role'] = data[1]
            st.rerun()
        else: st.error("Hatalı kullanıcı adı veya şifre")
else:
    # --- ANA UYGULAMA ---
    st.sidebar.title(f"👤 {st.session_state['user']}")
    st.sidebar.info(f"Yetki: {st.session_state['role']}")
    
    menu = ["📊 Dashboard & Raporlar", "🧪 Üretim & Reçete (BOM)", "📦 Depo & Hammadde", "💸 Finans & Satın Alma", "⚙️ Ayarlar"]
    if st.session_state['role'] != 'Yönetici': menu = ["🧪 Üretim & Reçete (BOM)", "📦 Depo & Hammadde"]
    
    choice = st.sidebar.selectbox("Modüller", menu)

    # 1. DASHBOARD & OTOMATİK RAPORLAMA
    if choice == "📊 Dashboard & Raporlar":
        st.header("📈 Kurumsal Performans")
        
        # Kritik Stok Uyarıları (Hammadde)
        kritik_h = pd.read_sql_query("SELECT ad, miktar, kritik_seviye FROM hammaddeler WHERE miktar <= kritik_seviye", conn)
        if not kritik_h.empty:
            for _, r in kritik_h.iterrows():
                st.warning(f"🚨 KRİTİK STOK: {r['ad']} (Mevcut: {r['miktar']}, Sınır: {r['kritik_seviye']})")

        col1, col2, col3 = st.columns(3)
        # Basit finansal veri
        ciro = pd.read_sql_query("SELECT SUM(miktar) FROM finans WHERE tip='Gelir'", conn).iloc[0,0] or 0
        gider = pd.read_sql_query("SELECT SUM(miktar) FROM finans WHERE tip='Gider'", conn).iloc[0,0] or 0
        col1.metric("Aylık Ciro", f"{ciro:,.2f} TL")
        col2.metric("Toplam Gider", f"{gider:,.2f} TL")
        col3.metric("Net Kâr", f"{(ciro-gider):,.2f} TL")

    # 2. ÜRETİM & REÇETE (BOM)
    elif choice == "🧪 Üretim & Reçete (BOM)":
        st.header("🧪 Reçete ve Üretim Yönetimi")
        tab1, tab2 = st.tabs(["Reçete Tanımla", "İş Emri & QR"])
        
        with tab1:
            st.subheader("Ürün Reçetesi (Bill of Materials)")
            # Reçete tanımlama kodları...
            st.info("Bu bölümde ürünlerin içindeki hammadde oranlarını (BOM) belirleyebilirsiniz.")

        with tab2:
            st.subheader("QR Destekli Üretim")
            # İş emri ve QR kod modülü...

    # 3. DEPO & HAMMADDE
    elif choice == "📦 Depo & Hammadde":
        st.header("📦 Hammadde ve Sarf Malzeme")
        with st.form("h_form"):
            h_ad = st.text_input("Hammadde Adı")
            h_mik = st.number_input("Miktar", min_value=0.0)
            h_birim = st.selectbox("Birim", ["KG", "Litre", "Adet (Kapak/Şişe)"])
            h_kritik = st.number_input("Kritik Seviye", min_value=1.0)
            if st.form_submit_button("Hammadde Ekle"):
                c.execute("INSERT INTO hammaddeler (ad, miktar, birim, kritik_seviye) VALUES (?,?,?,?)", (h_ad, h_mik, h_birim, h_kritik))
                conn.commit()
                st.success("Envanter güncellendi.")

    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state['logged_in'] = False
        st.rerun()
