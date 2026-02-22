import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# --- KURUMSAL KİMLİK VE MAVİ TEMA ---
st.set_page_config(page_title="Core Tarım | Meyvesuyu Planlama", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    [data-testid="stSidebar"] { background-color: #0c4a6e; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton>button {
        background-color: #0284c7;
        color: white;
        border-radius: 8px;
        font-weight: bold;
    }
    h1, h2, h3 { color: #0c4a6e; border-bottom: 2px solid #0284c7; padding-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı Bağlantısı
conn = sqlite3.connect('core_tarim_v4.db', check_same_thread=False)
c = conn.cursor()

# Tabloları Oluştur
c.execute('CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY, ad TEXT, tur TEXT, birim_fiyat REAL, stok_litre REAL)')
c.execute('CREATE TABLE IF NOT EXISTS musteriler (id INTEGER PRIMARY KEY, ad TEXT, bolge TEXT)')
c.execute('''CREATE TABLE IF NOT EXISTS satislar 
             (id INTEGER PRIMARY KEY, tarih DATE, urun_id INTEGER, musteri_id INTEGER, miktar_litre REAL, 
             toplam_tutar REAL, FOREIGN KEY(urun_id) REFERENCES urunler(id), FOREIGN KEY(musteri_id) REFERENCES musteriler(id))''')
conn.commit()

# --- ARAYÜZ ---
st.title("🥤 Core Tarım | Meyvesuyu Operasyon Paneli")
menu = ["📊 Satış & Pivot Analizi", "🧾 Yeni Satış Girişi", "🍎 Ürün / Meyve Tanımı", "📍 Bayi / Müşteri Kaydı"]
choice = st.sidebar.selectbox("Yönetim Menüsü", menu)

# 1. ÜRÜN TANIMI
if choice == "🍎 Ürün / Meyve Tanımı":
    st.subheader("Ürün Kataloğu Oluştur")
    col1, col2, col3 = st.columns(3)
    with col1: u_ad = st.text_input("Ürün Adı (Örn: %100 Elma Suyu)")
    with col2: u_fiyat = st.number_input("Litre Fiyatı (TL)", min_value=0.0)
    with col3: u_stok = st.number_input("Mevcut Stok (Litre)", min_value=0.0)
    
    if st.button("Sisteme Ekle"):
        c.execute("INSERT INTO urunler (ad, birim_fiyat, stok_litre) VALUES (?,?,?)", (u_ad, u_fiyat, u_stok))
        conn.commit()
        st.success(f"{u_ad} başarıyla kataloğa eklendi.")

    st.divider()
    st.subheader("Güncel Tank/Stok Durumu")
    st.dataframe(pd.read_sql_query("SELECT ad as 'Ürün', birim_fiyat as 'Litre Fiyatı', stok_litre as 'Litre (Stok)' FROM urunler", conn), use_container_width=True)

# 2. MÜŞTERİ KAYDI
elif choice == "📍 Bayi / Müşteri Kaydı":
    st.subheader("Bayi ve Müşteri Tanımlama")
    m_ad = st.text_input("Bayi/Firma Adı")
    m_bolge = st.selectbox("Bölge", ["Marmara", "Ege", "İç Anadolu", "Akdeniz", "Karadeniz", "Doğu/Güneydoğu"])
    if st.button("Bayiyi Kaydet"):
        c.execute("INSERT INTO musteriler (ad, bolge) VALUES (?,?)", (m_ad, m_bolge))
        conn.commit()
        st.success(f"{m_ad} ({m_bolge}) sisteme tanımlandı.")

# 3. SATIŞ GİRİŞİ
elif choice == "🧾 Yeni Satış Girişi":
    st.subheader("Satış ve Sevkiyat Kaydı")
    urunler_df = pd.read_sql_query("SELECT * FROM urunler", conn)
    musteriler_df = pd.read_sql_query("SELECT * FROM musteriler", conn)
    
    if not urunler_df.empty and not musteriler_df.empty:
        with st.form("core_satis"):
            secilen_urun = st.selectbox("Ürün Seçiniz", urunler_df['ad'])
            secilen_musteri = st.selectbox("Alıcı Bayi", musteriler_df['ad'])
            miktar = st.number_input("Satış Miktarı (Litre)", min_value=1.0)
            tarih = st.date_input("Sevkiyat Tarihi", date.today())
            submitted = st.form_submit_button("Satışı Onayla ve Stoktan Düş")

            if submitted:
                u_row = urunler_df[urunler_df['ad'] == secilen_urun].iloc[0]
                if u_row['stok_litre'] >= miktar:
                    toplam = miktar * u_row['birim_fiyat']
                    yeni_stok = u_row['stok_litre'] - miktar
                    c.execute("UPDATE urunler SET stok_litre = ? WHERE id = ?", (yeni_stok, int(u_row['id'])))
                    m_id = musteriler_df[musteriler_df['ad'] == secilen_musteri]['id'].values[0]
                    c.execute("INSERT INTO satislar (tarih, urun_id, musteri_id, miktar_litre, toplam_tutar) VALUES (?,?,?,?,?)",
                              (tarih, int(u_row['id']), int(m_id), miktar, toplam))
                    conn.commit()
                    st.success(f"Satış Onaylandı! Toplam Ciro: {toplam} TL")
                else:
                    st.error(f"Stok Yetersiz! Depoda sadece {u_row['stok_litre']} Litre ürün var.")
    else:
        st.warning("Lütfen önce Ürün ve Bayi tanımlaması yapın.")

# 4. PİVOT ANALİZ
elif choice == "📊 Satış & Pivot Analizi":
    st.subheader("Üretim ve Satış Pivot Tablosu")
    query = """
    SELECT s.tarih, u.ad as Urun, m.ad as Musteri, m.bolge as Bolge, s.miktar_litre, s.toplam_tutar 
    FROM satislar s
    JOIN urunler u ON s.urun_id = u.id
    JOIN musteriler m ON s.musteri_id = m.id
    """
    df = pd.read_sql_query(query, conn)
    
    if not df.empty:
        st.markdown("### 🔍 Bölge ve Ürün Bazlı Ciro Dağılımı")
        pivot = df.pivot_table(index='Urun', columns='Bolge', values='toplam_tutar', aggfunc='sum', margins=True).fillna(0)
        st.dataframe(pivot.style.format("{:.2f} TL"), use_container_width=True)
        
        st.markdown("### 📈 Aylık Satış Trendi (Litre)")
        df['tarih'] = pd.to_datetime(df['tarih'])
        st.line_chart(df.groupby('tarih')['miktar_litre'].sum())
    else:
        st.info("Sistemde henüz kayıtlı satış bulunmuyor.")
