import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import qrcode
from io import BytesIO

# --- KURUMSAL TEMA ---
st.set_page_config(page_title="Core Tarım | ERP v7.3", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    [data-testid="stSidebar"] { background-color: #0c4a6e; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton>button { background-color: #0284c7; color: white; border-radius: 8px; font-weight: bold; width: 100%; }
    .warning-card { background-color: #fff3cd; padding: 10px; border-radius: 8px; border-left: 5px solid #ffca2c; margin-bottom: 5px; color: #856404; }
    .danger-card { background-color: #f8d7da; padding: 10px; border-radius: 8px; border-left: 5px solid #dc3545; margin-bottom: 5px; color: #721c24; }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı Bağlantısı ve Tablo Onarımı
conn = sqlite3.connect('core_tarim_final_v7.db', check_same_thread=False)
c = conn.cursor()

# Tüm Tabloları Eksiksiz Oluştur
c.execute('CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY, ad TEXT, kategori TEXT, paketleme TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS stok_lotlari (id INTEGER PRIMARY KEY AUTOINCREMENT, urun_id INTEGER, miktar INTEGER, tett DATE)')
c.execute('CREATE TABLE IF NOT EXISTS is_emirleri (id INTEGER PRIMARY KEY AUTOINCREMENT, is_emri_no TEXT, urun_id INTEGER, hedef_miktar INTEGER, durum TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS satislar (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih DATE, urun_id INTEGER, adet INTEGER, tutar REAL)')
c.execute('CREATE TABLE IF NOT EXISTS giderler (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih DATE, tip TEXT, miktar REAL, aciklama TEXT)')
conn.commit()

# --- ÜRÜN KATALOĞU (Görsellerdeki Tüm Ürünler) ---
urun_katalogu = {
    "Meyve Suyu Grubu": [{"ad": "Nar Suyu", "paket": "200 ml"}, {"ad": "Limonata", "paket": "200 ml"}, {"ad": "Karadut Suyu", "paket": "200 ml"}, {"ad": "Portakal Suyu", "paket": "200 ml"}],
    "Reçel Grubu": [{"ad": "Kivi Reçeli", "paket": "375 g"}, {"ad": "İncir Reçeli", "paket": "375 g"}, {"ad": "Ahududu Reçeli", "paket": "375 g"}, {"ad": "Vişne Reçeli", "paket": "375 g"}],
    "Domates Grubu": [{"ad": "Domates Suyu", "paket": "1000 ml"}, {"ad": "Domates Rendesi", "paket": "500 g"}, {"ad": "Menemen Harcı", "paket": "500 g"}],
    "Ege Otları & Kapari": [{"ad": "Şevket-i Bostan", "paket": "320 g"}, {"ad": "Deniz Börülcesi", "paket": "350 g"}, {"ad": "Kapari", "paket": "190 g"}]
}

def qr_olustur(link):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- ARAYÜZ MANTIK ---
params = st.query_params
if "is_emri" in params:
    choice = "QR Personel Paneli"
else:
    choice = st.sidebar.selectbox("Yönetim Menüsü", [
        "📊 Finans & T.E.T.T. Takip", 
        "📋 İş Emirleri (Üretim)", 
        "📦 Ambar & Mevcut Ürün Girişi",
        "💸 Gider Kaydı",
        "🛒 Satış Ekranı"
    ])

# 1. FİNANS & TETT TAKİP
if choice == "📊 Finans & T.E.T.T. Takip":
    st.header("📊 Operasyonel Özet")
    
    # Finansal Hesaplama
    gelir = pd.read_sql_query("SELECT SUM(tutar) as t FROM satislar", conn)['t'].iloc[0] or 0
    gider = pd.read_sql_query("SELECT SUM(miktar) as t FROM giderler", conn)['t'].iloc[0] or 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Ciro", f"{gelir:,.2f} TL")
    col2.metric("Toplam Gider", f"{gider:,.2f} TL")
    col3.metric("Net Durum", f"{(gelir-gider):,.2f} TL")

    st.divider()
    # TETT Kontrol
    st.subheader("🕒 Yaklaşan T.E.T.T. Uyarıları")
    stok_df = pd.read_sql_query("SELECT sl.tett, u.ad, u.paketleme, sl.miktar FROM stok_lotlari sl JOIN urunler u ON sl.urun_id = u.id WHERE sl.miktar > 0", conn)
    if not stok_df.empty:
        stok_df['tett'] = pd.to_datetime(stok_df['tett']).dt.date
        bugun = date.today()
        for _, r in stok_df.iterrows():
            if r['tett'] < bugun:
                st.markdown(f"<div class='danger-card'>🚨 {r['ad']} ({r['paketleme']}) - {r['miktar']} Adet | GEÇMİŞ: {r['tett']}</div>", unsafe_allow_html=True)
            elif r['tett'] <= bugun + timedelta(days=30):
                st.markdown(f"<div class='warning-card'>⚠️ {r['ad']} ({r['paketleme']}) - {r['miktar']} Adet | KALAN: {r['tett']}</div>", unsafe_allow_html=True)
    else: st.info("Takip edilecek stok bulunmuyor.")

# 2. İŞ EMİRLERİ (ÜRETİM) - DÜZELTİLDİ
elif choice == "📋 İş Emirleri (Üretim)":
    st.header("📋 Üretim İş Emirleri")
    with st.form("new_work_order"):
        g = st.selectbox("Ürün Grubu", list(urun_katalogu.keys()))
        s = st.selectbox("Ürün Seç", [u['ad'] for u in urun_katalogu[g]])
        p = next(u['paket'] for u in urun_katalogu[g] if u['ad'] == s)
        h = st.number_input("Hedef Miktar", min_value=1)
        if st.form_submit_button("İş Emrini Ve QR Kodu Oluştur"):
            c.execute("SELECT id FROM urunler WHERE ad = ? AND paketleme = ?", (s, p))
            u = c.fetchone()
            u_id = u[0] if u else (c.execute("INSERT INTO urunler (ad, kategori, paketleme) VALUES (?,?,?)", (s, g, p)) or c.lastrowid)
            no = f"IE-{datetime.now().strftime('%d%H%M')}"
            c.execute("INSERT INTO is_emirleri (is_emri_no, urun_id, hedef_miktar, durum) VALUES (?,?,?,?)", (no, int(u_id), h, "Açık"))
            conn.commit()
            st.success(f"İş Emri {no} Yayınlandı!")

    st.subheader("Aktif İş Emirleri")
    emirler = pd.read_sql_query("SELECT ie.id, ie.is_emri_no, u.ad, u.paketleme FROM is_emirleri ie JOIN urunler u ON ie.urun_id = u.id WHERE ie.durum = 'Açık'", conn)
    for _, row in emirler.iterrows():
        c1, c2 = st.columns([3, 1])
        with c1: st.write(f"**{row['is_emri_no']}** | {row['ad']} ({row['paketleme']})")
        with c2:
            base_url = "https://meka10126-retim-planlama.streamlit.app"
            st.image(qr_olustur(f"{base_url}/?is_emri={row['id']}"), width=100)
        st.divider()

# 3. AMBAR & MEVCUT ÜRÜN GİRİŞİ - DÜZELTİLDİ
elif choice == "📦 Ambar & Mevcut Ürün Girişi":
    st.header("📦 Ambar ve Devir Girişi")
    with st.expander("➕ Mevcut Ürünü Sisteme Tanımla"):
        col1, col2 = st.columns(2)
        with col1:
            g_m = st.selectbox("Grup", list(urun_katalogu.keys()))
            s_m = st.selectbox("Ürün", [u['ad'] for u in urun_katalogu[g_m]])
        with col2:
            p_m = next(u['paket'] for u in urun_katalogu[g_m] if u['ad'] == s_m)
            m_m = st.number_input("Miktar", min_value=1)
            t_m = st.date_input("T.E.T.T.", date.today() + timedelta(days=180))
        if st.button("Stoğa Ekle"):
            c.execute("SELECT id FROM urunler WHERE ad = ? AND paketleme = ?", (s_m, p_m))
            u_row = c.fetchone()
            u_id = u_row[0] if u_row else (c.execute("INSERT INTO urunler (ad, kategori, paketleme) VALUES (?,?,?)", (s_m, g_m, p_m)) or c.lastrowid)
            c.execute("INSERT INTO stok_lotlari (urun_id, miktar, tett) VALUES (?,?,?)", (int(u_id), m_m, t_m))
            conn.commit()
            st.success("Mevcut stok kaydedildi.")

    st.subheader("📋 Güncel Stok Listesi")
    st_list = pd.read_sql_query("SELECT u.ad, u.paketleme, SUM(sl.miktar) as Toplam FROM stok_lotlari sl JOIN urunler u ON sl.urun_id = u.id GROUP BY u.id", conn)
    st.dataframe(st_list, use_container_width=True)

# 4. QR PERSONEL PANELİ (En Önemli Kısım)
elif choice == "QR Personel Paneli":
    ie_id = params["is_emri"]
    try:
        res = pd.read_sql_query(f"SELECT ie.*, u.ad, u.paketleme FROM is_emirleri ie JOIN urunler u ON ie.urun_id = u.id WHERE ie.id = {ie_id}", conn).iloc[0]
        st.title("🏭 Üretim Girişi")
        st.info(f"İş Emri: {res['is_emri_no']} | Ürün: {res['ad']} ({res['paketleme']})")
        miktar = st.number_input("Üretilen Miktar (Adet)", min_value=1)
        tett = st.date_input("T.E.T.T.", date.today() + timedelta(days=365))
        if st.button("KAYDET VE STOĞA EKLE"):
            c.execute("INSERT INTO stok_lotlari (urun_id, miktar, tett) VALUES (?,?,?)", (int(res['urun_id']), miktar, tett))
            conn.commit()
            st.success("Stok başarıyla güncellendi!")
    except:
        st.error("Geçersiz veya süresi dolmuş QR Kod!")

# 5. GİDER VE SATIŞ (Önceki Fonksiyonlar Basitleştirildi)
elif choice == "💸 Gider Kaydı":
    st.header("💸 Gider Girişi")
    t = st.selectbox("Tip", ["İşçilik", "Elektrik", "Ambalaj", "Hammadde", "Diğer"])
    m = st.number_input("Tutar", min_value=0.0)
    if st.button("Gideri İşle"):
        c.execute("INSERT INTO giderler (tarih, tip, miktar) VALUES (?,?,?)", (date.today(), t, m))
        conn.commit()
        st.success("Kaydedildi.")

elif choice == "🛒 Satış Ekranı":
    st.header("🛒 Satış Kaydı")
    u_df = pd.read_sql_query("SELECT id, ad, paketleme FROM urunler", conn)
    s_u = st.selectbox("Ürün", u_df['ad'] + " - " + u_df['paketleme'])
    s_m = st.number_input("Adet", min_value=1)
    s_t = st.number_input("Toplam Tutar", min_value=0.0)
    if st.button("Satışı Onayla"):
        u_id = u_df.iloc[u_df.index[u_df['ad'] + " - " + u_df['paketleme'] == s_u][0]]['id']
        c.execute("INSERT INTO satislar (tarih, urun_id, adet, tutar) VALUES (?,?,?,?)", (date.today(), int(u_id), s_m, s_t))
        conn.commit()
        st.success("Satış başarıyla işlendi.")
