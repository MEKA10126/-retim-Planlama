import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import qrcode
from io import BytesIO
import hashlib

# --- NETSIS TARZI PROFESYONEL TEMA ---
st.set_page_config(page_title="Core Tarım | Netsis Pro ERP", layout="wide")

st.markdown("""
    <style>
    /* Netsis Kurumsal Renk Paleti */
    :root {
        --main-bg: #f0f2f5;
        --sidebar-bg: #1e293b;
        --accent-blue: #0f172a;
        --netsis-grey: #e2e8f0;
    }
    
    .stApp { background-color: var(--main-bg); }
    
    /* Yan Menü (Sidebar) Tasarımı */
    [data-testid="stSidebar"] {
        background-color: var(--sidebar-bg);
        border-right: 2px solid #334155;
    }
    [data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    
    /* Netsis Tarzı Tablo ve Kart Yapısı */
    div.stDataFrame {
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        background-color: white;
    }
    
    /* Butonlar: Profesyonel ve Keskin Hatlı */
    .stButton>button {
        background-color: #334155;
        color: white;
        border-radius: 2px;
        border: 1px solid #1e293b;
        width: 100%;
        text-transform: uppercase;
        font-size: 12px;
        letter-spacing: 1px;
    }
    .stButton>button:hover {
        background-color: #0f172a;
        border-color: #0f172a;
    }

    /* Modül Başlıkları */
    h1, h2, h3 {
        color: #0f172a;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 600;
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı ve Şifreleme (Önceki altyapı korundu)
conn = sqlite3.connect('core_pro_netsis.db', check_same_thread=False)
c = conn.cursor()

def db_init():
    c.execute('CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY, ad TEXT, kategori TEXT, paketleme TEXT, stok INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS finans (id INTEGER PRIMARY KEY, tarih DATE, tip TEXT, miktar REAL, kalem TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS users (user TEXT PRIMARY KEY, pw TEXT, role TEXT)')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Admin')") # şifre: admin
    conn.commit()
db_init()

# --- GİRİŞ KONTROLÜ ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>SİSTEM GİRİŞİ</h2>", unsafe_allow_html=True)
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type='password')
        if st.button("SİSTEME BAĞLAN"):
            if u == "admin" and p == "admin": # Test için basit tutuldu
                st.session_state['auth'] = True
                st.rerun()
            else: st.error("Yetkisiz Erişim")
else:
    # --- NETSIS ANA MODÜLLER (Ağaç Yapısı) ---
    st.sidebar.markdown("### 🖥️ NETSIS MODÜLLERİ")
    
    # Hiyerarşik Menü
    modul = st.sidebar.radio("", [
        "🏠 Genel Dashboard",
        "📦 Stok Yönetimi",
        "🏭 Üretim Planlama (QR)",
        "💰 Cari & Finans Yönetimi",
        "🛠️ Sistem Ayarları"
    ])

    # 1. GENEL DASHBOARD
    if modul == "🏠 Genel Dashboard":
        st.title("📌 Kurumsal Kaynak Özeti")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Toplam Stok Değeri", "452.000 TL")
        k2.metric("Açık İş Emirleri", "12 Adet")
        k3.metric("Kritik T.E.T.T.", "3 Ürün", delta="-2", delta_color="inverse")
        k4.metric("Günlük Ciro", "14.250 TL")
        
        st.markdown("### 📈 Aylık Satış Trendi")
        st.area_chart(pd.DataFrame({'Gün': range(1,31), 'Satış': [x*100 for x in range(1,31)]}))

    # 2. STOK YÖNETİMİ
    elif modul == "📦 Stok Yönetimi":
        st.title("📦 Stok Kartları ve Ambar")
        t1, t2 = st.tabs(["Mevcut Stoklar", "Stok Giriş / Devir"])
        with t1:
            st.markdown("#### Ambar Bakiye Listesi")
            dummy_data = pd.DataFrame({
                'Ürün Kodu': ['MS-001', 'RC-012', 'DT-005'],
                'Ürün Adı': ['Nar Suyu 200ml', 'Çilek Reçeli 375g', 'Domates Rendesi'],
                'Miktar': [1250, 450, 800],
                'Birim': ['Adet', 'Adet', 'Adet']
            })
            st.table(dummy_data)
        with t2:
            st.subheader("Yeni Stok Giriş Fişi")
            # Kayıt formları buraya gelecek...

    # 3. ÜRETİM PLANLAMA
    elif modul == "🏭 Üretim Planlama (QR)":
        st.title("🏭 Üretim ve İş Emirleri")
        st.info("Bu modül üretim hatlarındaki QR istasyonlarını yönetir.")
        # QR ve İş emri kodları buraya entegre edilecek...

    # 4. CARİ & FİNANS
    elif modul == "💰 Cari & Finans Yönetimi":
        st.title("💰 Muhasebe ve Cari İşlemler")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.subheader("Gider Giriş Fişi")
            st.selectbox("Gider Tipi", ["Elektrik", "İşçilik", "Hammadde", "Lojistik"])
            st.number_input("Tutar", min_value=0.0)
            st.button("FİŞİ KAYDET")
        with col_f2:
            st.subheader("Gelir/Gider Dengesi")
            st.bar_chart({"Gelir": [15000], "Gider": [8500]})

    if st.sidebar.button("🔴 OTURUMU KAPAT"):
        st.session_state['auth'] = False
        st.rerun()
