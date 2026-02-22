import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import qrcode
from io import BytesIO

# --- KURUMSAL TEMA VE TASARIM ---
st.set_page_config(page_title="Core Tarım | İş Emri & QR", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #0c4a6e; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton>button { background-color: #0284c7; color: white; border-radius: 8px; font-weight: bold; }
    h1, h2, h3 { color: #0c4a6e; border-left: 5px solid #0284c7; padding-left: 15px; }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı Bağlantısı
conn = sqlite3.connect('core_tarim_final.db', check_same_thread=False)
c = conn.cursor()

# Tablo Yapıları
c.execute('''CREATE TABLE IF NOT EXISTS urunler 
             (id INTEGER PRIMARY KEY, ad TEXT, kategori TEXT, paketleme TEXT, stok_adet INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS is_emirleri 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, is_emri_no TEXT, urun_id INTEGER, hedef_miktar INTEGER, durum TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS satislar 
             (id INTEGER PRIMARY KEY, tarih DATE, urun_id INTEGER, adet INTEGER, tutar REAL)''')
conn.commit()

# --- ÜRÜN KATALOĞU (Görsellerden Alınan Sabit Veriler) ---
urun_katalogu = {
    "Meyve Suyu Grubu": [
        {"ad": "Nar Suyu", "paket": "200 ml Şişe"},
        {"ad": "Limonata", "paket": "200 ml Şişe"},
        {"ad": "Karadut Suyu", "paket": "200 ml Şişe"},
        {"ad": "Portakal Suyu", "paket": "200 ml Şişe"},
        {"ad": "Coremey Nar Suyu", "paket": "1000 ml Pet"},
        {"ad": "Coremey Limonata", "paket": "1000 ml Pet"},
        {"ad": "Nar Ekşisi", "paket": "250 g Şişe"}
    ],
    "Reçel Grubu": [
        {"ad": "Kivi Reçeli", "paket": "375 g Kavanoz"},
        {"ad": "İncir Reçeli", "paket": "375 g Kavanoz"},
        {"ad": "Ahududu Reçeli", "paket": "375 g Kavanoz"},
        {"ad": "Vişne Reçeli", "paket": "375 g Kavanoz"},
        {"ad": "Portakal Reçeli", "paket": "375 g Kavanoz"}
    ],
    "Domates & Sos Grubu": [
        {"ad": "Domates Suyu", "paket": "1000 ml Şişe"},
        {"ad": "Domates Rendesi", "paket": "500 g Kavanoz"},
        {"ad": "Doğranmış Domates", "paket": "500 g Kavanoz"},
        {"ad": "Menemen Harcı", "paket": "500 g Kavanoz"}
    ],
    "Ege Otları & Kapari": [
        {"ad": "Şevket-i Bostan", "paket": "320 g Net"},
        {"ad": "Deniz Börülcesi", "paket": "350 g Net"},
        {"ad": "Enginar Kalbi", "paket": "360 g Net"},
        {"ad": "Kapari Meyvesi", "paket": "700 g Kavanoz"},
        {"ad": "Kapari", "paket": "190 g Kavanoz"}
    ]
}

# QR Fonksiyonu
def qr_olustur(link):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- ARAYÜZ ---
params = st.query_params
if "is_emri" in params:
    choice = "QR Personel Paneli"
else:
    choice = st.sidebar.selectbox("Yönetim Menüsü", ["📋 İş Emirleri", "📦 Ambar & Stok", "📊 Satış Analizi"])

# 1. İŞ EMİRLERİ (Yönetici)
if choice == "📋 İş Emirleri":
    st.header("📋 Üretim İş Emirleri")
    
    with st.expander("➕ Yeni İş Emri Tanımla"):
        kat = st.selectbox("Ürün Grubu", list(urun_katalogu.keys()))
        secilen = st.selectbox("Ürün", [u['ad'] for u in urun_katalogu[kat]])
        paket = next(u['paket'] for u in urun_katalogu[kat] if u['ad'] == secilen)
        hedef = st.number_input("Hedef Üretim (Adet)", min_value=1)
        
        if st.button("İş Emrini Oluştur"):
            # Önce ürün var mı kontrol et, yoksa ekle
            c.execute("SELECT id FROM urunler WHERE ad = ? AND paketleme = ?", (secilen, paket))
            u_row = c.fetchone()
            if not u_row:
                c.execute("INSERT INTO urunler (ad, kategori, paketleme, stok_adet) VALUES (?,?,?,0)", (secilen, kat, paket))
                u_id = c.lastrowid
            else:
                u_id = u_row[0]
            
            no = f"IE-{datetime.now().strftime('%d%H%M')}"
            c.execute("INSERT INTO is_emirleri (is_emri_no, urun_id, hedef_miktar, durum) VALUES (?,?,?,?)", (no, u_id, hedef, "Açık"))
            conn.commit()
            st.success("İş emri oluşturuldu!")

    st.divider()
    st.subheader("Aktif Emirler ve QR Kodlar")
    emirler = pd.read_sql_query("SELECT ie.id, ie.is_emri_no, u.ad, u.paketleme, ie.hedef_miktar FROM is_emirleri ie JOIN urunler u ON ie.urun_id = u.id WHERE ie.durum = 'Açık'", conn)
    
    for _, row in emirler.iterrows():
        c1, c2 = st.columns([3, 1])
        with c1: st.write(f"**{row['is_emri_no']}** | {row['ad']} ({row['paketleme']}) - Hedef: {row['hedef_miktar']}")
        with c2:
            # ÖNEMLİ: Linki kendi Streamlit URL'nizle güncelleyin
            base_url = "https://meka10126-planlama.streamlit.app" 
            qr_img = qr_olustur(f"{base_url}/?is_emri={row['id']}")
            st.image(qr_img, width=80)
        st.divider()

# 2. QR PERSONEL PANELİ (Sadece QR ile erişilir)
elif choice == "QR Personel Paneli":
    ie_id = params["is_emri"]
    res = pd.read_sql_query(f"SELECT ie.*, u.ad, u.paketleme, u.stok_adet FROM is_emirleri ie JOIN urunler u ON ie.urun_id = u.id WHERE ie.id = {ie_id}", conn).iloc[0]
    
    st.success(f"BAĞLANDI: {res['is_emri_no']}")
    st.title(f"{res['ad']}")
    st.info(f"Paketleme: {res['paketleme']} | Mevcut Stok: {res['stok_adet']}")
    
    adet = st.number_input("İşlem Adedi", min_value=1)
    if st.button("➕ STOĞA EKLE"):
        c.execute("UPDATE urunler SET stok_adet = stok_adet + ? WHERE id = ?", (adet, int(res['urun_id'])))
        conn.commit()
        st.success("Stok güncellendi!")
        st.rerun()

# 3. AMBAR & STOK
elif choice == "📦 Ambar & Stok":
    st.header("📦 Genel Ambar Durumu")
    stok_df = pd.read_sql_query("SELECT kategori, ad, paketleme, stok_adet FROM urunler", conn)
    st.dataframe(stok_df, use_container_width=True)
