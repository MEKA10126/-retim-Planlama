import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Veritabanı Fonksiyonları
def create_connection():
    conn = sqlite3.connect('netsis_v2.db', check_same_thread=False)
    return conn

conn = create_connection()
c = conn.cursor()

# Tabloları Hazırla
c.execute('CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY, ad TEXT, birim_fiyat REAL)')
c.execute('CREATE TABLE IF NOT EXISTS musteriler (id INTEGER PRIMARY KEY, ad TEXT, sehir TEXT)')
c.execute('''CREATE TABLE IF NOT EXISTS satislar 
             (id INTEGER PRIMARY KEY, tarih DATE, urun_id INTEGER, musteri_id INTEGER, miktar REAL, 
             toplam_tutar REAL, FOREIGN KEY(urun_id) REFERENCES urunler(id), FOREIGN KEY(musteri_id) REFERENCES musteriler(id))''')
conn.commit()

# --- ARAYÜZ ---
st.set_page_config(page_title="Mühendislik ERP v2", layout="wide")
menu = ["Satış Paneli", "Ürün Tanımlama", "Müşteri Tanımlama", "Pivot Raporlar"]
choice = st.sidebar.selectbox("Modül Seçiniz", menu)

# 1. ÜRÜN TANIMLAMA
if choice == "Ürün Tanımlama":
    st.subheader("📦 Ürün Kartı Oluştur")
    u_ad = st.text_input("Ürün Adı")
    u_fiyat = st.number_input("Birim Fiyat", min_value=0.0)
    if st.button("Ürünü Kaydet"):
        c.execute("INSERT INTO urunler (ad, birim_fiyat) VALUES (?,?)", (u_ad, u_fiyat))
        conn.commit()
        st.success(f"{u_ad} başarıyla eklendi.")

# 2. MÜŞTERİ TANIMLAMA
elif choice == "Müşteri Tanımlama":
    st.subheader("👥 Müşteri (Cari) Kartı Oluştur")
    m_ad = st.text_input("Müşteri/Firma Adı")
    m_sehir = st.text_input("Şehir")
    if st.button("Müşteriyi Kaydet"):
        c.execute("INSERT INTO musteriler (ad, sehir) VALUES (?,?)", (m_ad, m_sehir))
        conn.commit()
        st.success(f"{m_ad} başarıyla eklendi.")

# 3. SATIŞ PANELİ
elif choice == "Satış Paneli":
    st.subheader("💰 Satış Kaydı")
    
    # Verileri Çek
    urunler_df = pd.read_sql_query("SELECT * FROM urunler", conn)
    musteriler_df = pd.read_sql_query("SELECT * FROM musteriler", conn)
    
    col1, col2 = st.columns(2)
    with col1:
        secilen_urun = st.selectbox("Ürün", urunler_df['ad'] if not urunler_df.empty else ["Önce Ürün Ekleyin"])
        miktar = st.number_input("Miktar", min_value=0.1)
    with col2:
        secilen_musteri = st.selectbox("Müşteri", musteriler_df['ad'] if not musteriler_df.empty else ["Önce Müşteri Ekleyin"])
        tarih = st.date_input("Tarih", datetime.now())

    if st.button("Satışı Onayla"):
        u_id = urunler_df[urunler_df['ad'] == secilen_urun]['id'].values[0]
        m_id = musteriler_df[musteriler_df['ad'] == secilen_musteri]['id'].values[0]
        fiyat = urunler_df[urunler_df['ad'] == secilen_urun]['birim_fiyat'].values[0]
        toplam = miktar * fiyat
        
        c.execute("INSERT INTO satislar (tarih, urun_id, musteri_id, miktar, toplam_tutar) VALUES (?,?,?,?,?)",
                  (tarih, int(u_id), int(m_id), miktar, toplam))
        conn.commit()
        st.balloons()
        st.success(f"Satış Kaydedildi! Toplam: {toplam} TL")

# 4. PİVOT RAPORLAR (İstediğin Kritik Bölüm)
elif choice == "Pivot Raporlar":
    st.subheader("📈 Satış Analiz ve Pivot Tablo")
    
    query = """
    SELECT s.tarih, u.ad as Urun, m.ad as Musteri, s.miktar, s.toplam_tutar 
    FROM satislar s
    JOIN urunler u ON s.urun_id = u.id
    JOIN musteriler m ON s.musteri_id = m.id
    """
    df = pd.read_sql_query(query, conn)
    
    if not df.empty:
        # Pivot Seçenekleri
        st.markdown("### Dinamik Pivot")
        pivot_result = df.pivot_table(
            index='Urun', 
            columns='Musteri', 
            values='toplam_tutar', 
            aggfunc='sum', 
            margins=True # Toplam satırını ekler
        ).fillna(0)
        
        st.dataframe(pivot_result.style.format("{:.2f} TL"))
        
        st.markdown("### Zaman Çizelgesi")
        st.line_chart(df.groupby('tarih')['toplam_tutar'].sum())
    else:
        st.warning("Raporlayacak veri bulunamadı.")
