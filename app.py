import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import io

# --- MAVİ TEMA VE TASARIM AYARLARI ---
st.set_page_config(page_title="Mühendislik ERP v3.1", layout="wide")

# CSS ile Mavi Tema Uygulama
st.markdown("""
    <style>
    /* Ana arka plan ve metin renkleri */
    .stApp {
        background-color: #f0f2f6;
    }
    /* Kenar çubuğu (Sidebar) mavi tonu */
    [data-testid="stSidebar"] {
        background-color: #1e3a8a;
    }
    [data-testid="stSidebar"] .stSelectbox label, [data-testid="stSidebar"] .stMarkdown p {
        color: white !important;
    }
    /* Butonları mavi yap */
    .stButton>button {
        background-color: #2563eb;
        color: white;
        border-radius: 5px;
        border: none;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
        border: none;
    }
    /* Başlık rengi */
    h1, h2, h3 {
        color: #1e3a8a;
    }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı Fonksiyonları
def create_connection():
    conn = sqlite3.connect('netsis_v3.db', check_same_thread=False)
    return conn

conn = create_connection()
c = conn.cursor()

# Tablo Yapıları
c.execute('CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY, ad TEXT, birim_fiyat REAL, stok_miktari REAL)')
c.execute('CREATE TABLE IF NOT EXISTS musteriler (id INTEGER PRIMARY KEY, ad TEXT, sehir TEXT)')
c.execute('''CREATE TABLE IF NOT EXISTS satislar 
             (id INTEGER PRIMARY KEY, tarih DATE, urun_id INTEGER, musteri_id INTEGER, miktar REAL, 
             toplam_tutar REAL, FOREIGN KEY(urun_id) REFERENCES urunler(id), FOREIGN KEY(musteri_id) REFERENCES musteriler(id))''')
conn.commit()

# --- ARAYÜZ ---
menu = ["📊 Dashboard & Pivot", "💰 Satış Paneli", "📦 Ürün Yönetimi", "👥 Müşteri Kartları"]
choice = st.sidebar.selectbox("Modül Seçiniz", menu)

# 1. ÜRÜN YÖNETİMİ
if choice == "📦 Ürün Yönetimi":
    st.subheader("🔵 Ürün ve Stok Tanımlama")
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1: u_ad = st.text_input("Ürün Adı")
        with col2: u_fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.0)
        with col3: u_stok = st.number_input("Başlangıç Stoğu", min_value=0.0)
        
        if st.button("Ürünü Kaydet"):
            c.execute("INSERT INTO urunler (ad, birim_fiyat, stok_miktari) VALUES (?,?,?)", (u_ad, u_fiyat, u_stok))
            conn.commit()
            st.success(f"{u_ad} stoklara eklendi.")

    st.divider()
    st.subheader("🔵 Aktüel Stok Durumu")
    st.dataframe(pd.read_sql_query("SELECT ad as 'Ürün', birim_fiyat as 'Fiyat', stok_miktari as 'Mevcut Stok' FROM urunler", conn), use_container_width=True)

# 2. MÜŞTERİ KARTLARI
elif choice == "👥 Müşteri Kartları":
    st.subheader("🔵 Cari Hesap Tanımlama")
    m_ad = st.text_input("Müşteri/Firma Adı")
    m_sehir = st.text_input("Şehir")
    if st.button("Müşteriyi Kaydet"):
        c.execute("INSERT INTO musteriler (ad, sehir) VALUES (?,?)", (m_ad, m_sehir))
        conn.commit()
        st.success(f"{m_ad} başarıyla kaydedildi.")

# 3. SATIŞ PANELİ
elif choice == "💰 Satış Paneli":
    st.subheader("🔵 Yeni Satış Oluştur")
    urunler_df = pd.read_sql_query("SELECT * FROM urunler", conn)
    musteriler_df = pd.read_sql_query("SELECT * FROM musteriler", conn)
    
    if not urunler_df.empty and not musteriler_df.empty:
        with st.form("satis_form"):
            secilen_urun = st.selectbox("Satılacak Ürün", urunler_df['ad'])
            secilen_musteri = st.selectbox("Müşteri", musteriler_df['ad'])
            miktar = st.number_input("Miktar", min_value=0.1)
            tarih = st.date_input("Satış Tarihi", date.today())
            submitted = st.form_submit_button("Satışı Onayla")

            if submitted:
                u_row = urunler_df[urunler_df['ad'] == secilen_urun].iloc[0]
                if u_row['stok_miktari'] >= miktar:
                    toplam = miktar * u_row['birim_fiyat']
                    yeni_stok = u_row['stok_miktari'] - miktar
                    c.execute("UPDATE urunler SET stok_miktari = ? WHERE id = ?", (yeni_stok, int(u_row['id'])))
                    m_id = musteriler_df[musteriler_df['ad'] == secilen_musteri]['id'].values[0]
                    c.execute("INSERT INTO satislar (tarih, urun_id, musteri_id, miktar, toplam_tutar) VALUES (?,?,?,?,?)",
                              (tarih, int(u_row['id']), int(m_id), miktar, toplam))
                    conn.commit()
                    st.success(f"Satış Tamamlandı! Kalan Stok: {yeni_stok}")
                    
                    fatura_icerik = f"SATIŞ FATURASI\nTarih: {tarih}\nMüşteri: {secilen_musteri}\nÜrün: {secilen_urun}\nMiktar: {miktar}\nToplam: {toplam} TL"
                    st.download_button("📄 Fatura İndir", fatura_icerik, file_name=f"fatura_{secilen_musteri}.txt")
                else:
                    st.error("Yetersiz Stok!")
    else:
        st.warning("Lütfen önce ürün ve müşteri tanımlayın.")

# 4. DASHBOARD & PİVOT
elif choice == "📊 Dashboard & Pivot":
    st.subheader("🔵 Satış Analizi ve Pivot Tablolar")
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("Başlangıç", date(2025, 1, 1))
    with col2: end_date = st.date_input("Bitiş", date.today())

    query = """
    SELECT s.tarih, u.ad as Urun, m.ad as Musteri, s.miktar, s.toplam_tutar 
    FROM satislar s
    JOIN urunler u ON s.urun_id = u.id
    JOIN musteriler m ON s.musteri_id = m.id
    WHERE s.tarih BETWEEN ? AND ?
    """
    df = pd.read_sql_query(query, conn, params=(start_date, end_date))
    
    if not df.empty:
        st.markdown("### 🔍 Ürün / Müşteri Pivot Analizi")
        pivot = df.pivot_table(index='Urun', columns='Musteri', values='toplam_tutar', aggfunc='sum', margins=True).fillna(0)
        st.dataframe(pivot.style.format("{:.2f} TL"), use_container_width=True)
        
        st.markdown("### 📅 Günlük Ciro Trendi")
        df['tarih'] = pd.to_datetime(df['tarih'])
        st.line_chart(df.groupby('tarih')['toplam_tutar'].sum())
    else:
        st.info("Veri bulunamadı.")
