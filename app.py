import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import qrcode
from io import BytesIO

# --- KURUMSAL TEMA ---
st.set_page_config(page_title="Core Tarım | T.E.T.T. Kontrol", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    [data-testid="stSidebar"] { background-color: #0c4a6e; }
    .stButton>button { background-color: #0284c7; color: white; border-radius: 8px; font-weight: bold; }
    .warning-card { background-color: #fff3cd; padding: 15px; border-radius: 10px; border-left: 5px solid #ffca2c; }
    .danger-card { background-color: #f8d7da; padding: 15px; border-radius: 10px; border-left: 5px solid #dc3545; }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı Bağlantısı
conn = sqlite3.connect('core_tarim_v7.db', check_same_thread=False)
c = conn.cursor()

# Tabloları Güncelle (TETT Eklendi)
c.execute('''CREATE TABLE IF NOT EXISTS urunler 
             (id INTEGER PRIMARY KEY, ad TEXT, kategori TEXT, paketleme TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS stok_lotlari 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, urun_id INTEGER, miktar INTEGER, tett DATE)''')
c.execute('''CREATE TABLE IF NOT EXISTS is_emirleri 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, is_emri_no TEXT, urun_id INTEGER, hedef_miktar INTEGER, durum TEXT)''')
conn.commit()

# --- ÜRÜN KATALOĞU ---
urun_katalogu = {
    "Meyve Suyu Grubu": [{"ad": "Nar Suyu", "paket": "200 ml"}, {"ad": "Limonata", "paket": "200 ml"}],
    "Reçel Grubu": [{"ad": "Kivi Reçeli", "paket": "375 g"}, {"ad": "İncir Reçeli", "paket": "375 g"}],
    "Domates Grubu": [{"ad": "Domates Suyu", "paket": "1000 ml"}]
}

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
    choice = st.sidebar.selectbox("Yönetim Menüsü", ["📊 Dashboard & TETT Uyarı", "📋 İş Emirleri", "📦 Ambar Durumu"])

# 1. DASHBOARD & TETT UYARI
if choice == "📊 Dashboard & TETT Uyarı":
    st.header("🕒 T.E.T.T. Takip ve Uyarı Sistemi")
    
    # Tüm stok lotlarını çek
    stok_df = pd.read_sql_query("""
        SELECT sl.tett, u.ad, u.paketleme, sl.miktar 
        FROM stok_lotlari sl JOIN urunler u ON sl.urun_id = u.id
        WHERE sl.miktar > 0
    """, conn)
    
    if not stok_df.empty:
        stok_df['tett'] = pd.to_datetime(stok_df['tett']).dt.date
        bugun = date.today()
        kritik_gun = bugun + timedelta(days=30)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("❌ Tarihi Geçen Ürünler")
            gecenler = stok_df[stok_df['tett'] < bugun]
            if not gecenler.empty:
                for _, r in gecenler.iterrows():
                    st.markdown(f"<div class='danger-card'><b>{r['ad']}</b> ({r['paketleme']})<br>TETT: {r['tett']} | Miktar: {r['miktar']} Adet</div>", unsafe_allow_html=True)
            else: st.success("Tarihi geçmiş ürün bulunmuyor.")

        with col2:
            st.subheader("⚠️ Yaklaşan T.E.T.T. (Son 30 Gün)")
            yaklasanlar = stok_df[(stok_df['tett'] >= bugun) & (stok_df['tett'] <= kritik_gun)]
            if not yaklasanlar.empty:
                for _, r in yaklasanlar.iterrows():
                    st.markdown(f"<div class='warning-card'><b>{r['ad']}</b> ({r['paketleme']})<br>TETT: {r['tett']} | Miktar: {r['miktar']} Adet</div>", unsafe_allow_html=True)
            else: st.info("Yakın zamanda süresi dolacak ürün yok.")
    else:
        st.info("Henüz stok girişi yapılmamış.")

# 2. İŞ EMİRLERİ
elif choice == "📋 İş Emirleri":
    st.header("📋 Üretim İş Emirleri")
    with st.expander("➕ Yeni İş Emri Oluştur"):
        kat = st.selectbox("Grup", list(urun_katalogu.keys()))
        secilen = st.selectbox("Ürün", [u['ad'] for u in urun_katalogu[kat]])
        paket = next(u['paket'] for u in urun_katalogu[kat] if u['ad'] == secilen)
        if st.button("Emri Yayınla"):
            c.execute("SELECT id FROM urunler WHERE ad = ? AND paketleme = ?", (secilen, paket))
            u = c.fetchone()
            if not u:
                c.execute("INSERT INTO urunler (ad, kategori, paketleme) VALUES (?,?,?)", (secilen, kat, paket))
                u_id = c.lastrowid
            else: u_id = u[0]
            no = f"IE-{datetime.now().strftime('%d%H%M')}"
            c.execute("INSERT INTO is_emirleri (is_emri_no, urun_id, hedef_miktar, durum) VALUES (?,?,?,?)", (no, u_id, 0, "Açık"))
            conn.commit()
            st.success("İş emri hazır!")

    st.subheader("Aktif QR Kodlar")
    emirler = pd.read_sql_query("SELECT ie.id, ie.is_emri_no, u.ad, u.paketleme FROM is_emirleri ie JOIN urunler u ON ie.urun_id = u.id WHERE ie.durum='Açık'", conn)
    for _, row in emirler.iterrows():
        c1, c2 = st.columns([4, 1])
        with c1: st.write(f"**{row['is_emri_no']}** - {row['ad']} ({row['paketleme']})")
        with c2:
            base_url = "https://meka10126-retim-planlama.streamlit.app" # BURAYI KENDİ LİNKİNLE GÜNCELLE
            st.image(qr_olustur(f"{base_url}/?is_emri={row['id']}"), width=80)

# 3. QR PERSONEL PANELİ
elif choice == "QR Personel Paneli":
    ie_id = params["is_emri"]
    res = pd.read_sql_query(f"SELECT ie.*, u.ad, u.paketleme FROM is_emirleri ie JOIN urunler u ON ie.urun_id = u.id WHERE ie.id = {ie_id}", conn).iloc[0]
    
    st.title("⚡ Hızlı Üretim Girişi")
    st.subheader(f"{res['ad']} ({res['paketleme']})")
    
    adet = st.number_input("Üretilen Adet", min_value=1)
    tett_tarih = st.date_input("T.E.T.T. Seçiniz", date.today() + timedelta(days=365))
    
    if st.button("✅ STOĞA EKLE"):
        c.execute("INSERT INTO stok_lotlari (urun_id, miktar, tett) VALUES (?,?,?)", (int(res['urun_id']), adet, tett_tarih))
        conn.commit()
        st.success("Stok ve T.E.T.T. başarıyla kaydedildi!")
