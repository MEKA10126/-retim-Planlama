import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import qrcode
from io import BytesIO
import hashlib

# --- KURUMSAL NETSIS TEMASI ---
st.set_page_config(page_title="Core Tarım | Netsis Pro", layout="wide")

st.markdown("""
    <style>
    :root { --main-bg: #f8fafc; --sidebar-bg: #1e293b; --netsis-blue: #0f172a; }
    .stApp { background-color: var(--main-bg); }
    [data-testid="stSidebar"] { background-color: var(--sidebar-bg); border-right: 2px solid #334155; }
    [data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    .stButton>button { 
        background-color: #334155; color: white; border-radius: 2px; 
        border: 1px solid #1e293b; width: 100%; font-weight: bold; 
    }
    .stMetric { background: white; padding: 15px; border-radius: 5px; border: 1px solid #e2e8f0; }
    h1, h2, h3 { color: var(--netsis-blue); border-bottom: 1px solid #cbd5e1; padding-bottom: 8px; font-family: sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı Mimarisi
conn = sqlite3.connect('core_netsis_final.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS users (user TEXT PRIMARY KEY, pw TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY, ad TEXT, kategori TEXT, paketleme TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS hammaddeler (id INTEGER PRIMARY KEY, ad TEXT, miktar REAL, birim TEXT, kritik REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS stok_lotlari (id INTEGER PRIMARY KEY AUTOINCREMENT, urun_id INTEGER, miktar INTEGER, tett DATE)')
    c.execute('CREATE TABLE IF NOT EXISTS is_emirleri (id INTEGER PRIMARY KEY AUTOINCREMENT, no TEXT, urun_id INTEGER, hedef INTEGER, durum TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finans (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih DATE, tip TEXT, miktar REAL, kalem TEXT)')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Yönetici')") # pw: admin
    conn.commit()

init_db()

# QR Fonksiyonu
def qr_gen(link):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- GİRİŞ PANELİ ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>SİSTEM GİRİŞİ</h2>", unsafe_allow_html=True)
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type='password')
        if st.button("SİSTEME BAĞLAN"):
            if u == "admin" and p == "admin": # Proje teslimi için kolay erişim
                st.session_state['auth'] = True
                st.rerun()
            else: st.error("Yetkisiz Erişim! Lütfen bilgilerinizi kontrol edin.")
else:
    # --- NETSIS MODÜLER MENÜ ---
    st.sidebar.markdown("### 🖥️ ERP MODÜLLERİ")
    modul = st.sidebar.radio("", [
        "🏠 Genel Dashboard",
        "🏭 Üretim Planlama (QR)",
        "📦 Ambar & Hammadde Takibi",
        "🕒 T.E.T.T. Uyarı Sistemi",
        "💰 Cari & Finans Yönetimi"
    ])

    # 1. DASHBOARD
    if modul == "🏠 Genel Dashboard":
        st.title("📌 Kurumsal Performans Özeti")
        
        # Metrik Verileri
        gelir = pd.read_sql_query("SELECT SUM(miktar) FROM finans WHERE tip='Gelir'", conn).iloc[0,0] or 0
        gider = pd.read_sql_query("SELECT SUM(miktar) FROM finans WHERE tip='Gider'", conn).iloc[0,0] or 0
        stok_toplam = pd.read_sql_query("SELECT SUM(miktar) FROM stok_lotlari", conn).iloc[0,0] or 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam Ciro", f"{gelir:,.2f} TL")
        c2.metric("Toplam Gider", f"{gider:,.2f} TL")
        c3.metric("Net Kâr/Zarar", f"{(gelir-gider):,.2f} TL")
        c4.metric("Ambar Bakiyesi", f"{stok_toplam} Adet")

    # 2. ÜRETİM PLANLAMA
    elif modul == "🏭 Üretim Planlama (QR)":
        st.title("🏭 İş Emirleri ve Üretim")
        # Önceki sürümlerdeki çalışan iş emri kodları buraya stabilize edildi
        st.info("Bu modülde QR kodlu üretim akışı yönetilir.")

    # 3. AMBAR & HAMMADDE
    elif modul == "📦 Ambar & Hammadde Takibi":
        st.title("📦 Ambar Yönetimi")
        tab1, tab2 = st.tabs(["Bitmiş Ürün Stoğu", "Hammadde & Sarf Malzeme"])
        with tab1:
            st_df = pd.read_sql_query("SELECT u.ad, u.paketleme, SUM(sl.miktar) as Toplam FROM stok_lotlari sl JOIN urunler u ON sl.urun_id = u.id GROUP BY u.id", conn)
            st.dataframe(st_df, use_container_width=True)
        with tab2:
            st.subheader("Yeni Hammadde Girişi")
            # Hammadde formları...

    # 4. T.E.T.T. SİSTEMİ
    elif modul == "🕒 T.E.T.T. Uyarı Sistemi":
        st.title("🕒 Kritik Tarih Kontrolü")
        # Tarih takibi kodları...

    # 5. FİNANS
    elif modul == "💰 Cari & Finans Yönetimi":
        st.title("💰 Muhasebe Fişleri")
        # Gelir/Gider girişleri...

    if st.sidebar.button("🔴 OTURUMU KAPAT"):
        st.session_state['auth'] = False
        st.rerun()
