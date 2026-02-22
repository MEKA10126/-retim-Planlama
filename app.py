import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# --- KURUMSAL TEMA AYARLARI ---
st.set_page_config(page_title="Core Tarım | Operasyon Merkezi", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #075e54; } /* Core Tarım Yeşili/Mavisi */
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton>button {
        background-color: #10b981;
        color: white;
        border-radius: 12px;
        height: 3em;
        font-weight: bold;
    }
    h1, h2, h3 { color: #064e3b; border-left: 5px solid #10b981; padding-left: 15px; }
    .stDataFrame { border: 1px solid #e2e8f0; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı Bağlantısı
conn = sqlite3.connect('core_tarim_v5.db', check_same_thread=False)
c = conn.cursor()

# Gelişmiş Tablo Yapısı
c.execute('''CREATE TABLE IF NOT EXISTS urunler 
             (id INTEGER PRIMARY KEY, ad TEXT, kategori TEXT, paketleme TEXT, birim_fiyat REAL, stok_adet INTEGER)''')
c.execute('CREATE TABLE IF NOT EXISTS musteriler (id INTEGER PRIMARY KEY, ad TEXT, bolge TEXT)')
c.execute('''CREATE TABLE IF NOT EXISTS satislar 
             (id INTEGER PRIMARY KEY, tarih DATE, urun_id INTEGER, musteri_id INTEGER, adet INTEGER, 
             toplam_tutar REAL, FOREIGN KEY(urun_id) REFERENCES urunler(id), FOREIGN KEY(musteri_id) REFERENCES musteriler(id))''')
conn.commit()

# --- ÜRÜN KATALOĞU (Görsellerden Çıkarılan Veriler) ---
urun_katalogu = {
    "Meyve Suyu Grubu": [
        {"ad": "Nar Suyu", "paket": "200 ml Şişe"},
        {"ad": "Limonata", "paket": "200 ml Şişe"},
        {"ad": "Karadut Suyu", "paket": "200 ml Şişe"},
        {"ad": "Portakal Suyu", "paket": "200 ml Şişe"},
        {"ad": "Coremey Serisi", "paket": "1000 ml Pet"},
        {"ad": "Nar Ekşisi", "paket": "250 g Şişe"}
    ],
    "Reçel Grubu (375g)": [
        {"ad": "Kivi Reçeli", "paket": "375 g Kavanoz"},
        {"ad": "İncir Reçeli", "paket": "375 g Kavanoz"},
        {"ad": "Ahududu Reçeli", "paket": "375 g Kavanoz"},
        {"ad": "Çilek & Kayısı Reçeli", "paket": "375 g Kavanoz"},
        {"ad": "Vişne Reçeli", "paket": "375 g Kavanoz"}
    ],
    "Domates Grubu": [
        {"ad": "Domates Suyu", "paket": "1000 ml Şişe"},
        {"ad": "Domates Rendesi", "paket": "500 g Kavanoz"},
        {"ad": "Doğranmış Domates", "paket": "500 g Kavanoz"},
        {"ad": "Menemen Harcı", "paket": "500 g Kavanoz"}
    ],
    "Ege Otları & Kapari": [
        {"ad": "Şevket-i Bostan", "paket": "320 g Net Kavanoz"},
        {"ad": "Deniz Börülcesi", "paket": "350 g Net Kavanoz"},
        {"ad": "Enginar Kalbi", "paket": "360 g Net Kavanoz"},
        {"ad": "Kapari Meyvesi", "paket": "700 g Kavanoz"},
        {"ad": "Kapari", "paket": "190 g Kavanoz"}
    ]
}

# --- ARAYÜZ ---
st.title("🌿 Core Tarım | Üretim ve Satış Yönetimi")
menu = ["📈 Analiz Paneli", "📦 Üretim / Stok Girişi", "🛒 Satış Ekranı", "👥 Bayi Tanımlama"]
choice = st.sidebar.selectbox("Menü", menu)

# 1. ÜRETİM / STOK GİRİŞİ (Hızlı Seçim Ekranı)
if choice == "📦 Üretim / Stok Girişi":
    st.subheader("Üretimden Gelen Ürünleri Stoğa Ekle")
    
    kat = st.selectbox("Ürün Grubu Seçiniz", list(urun_katalogu.keys()))
    secilen_alt_urun = st.selectbox("Ürün Seçiniz", [u['ad'] for u in urun_katalogu[kat]])
    
    # Seçilen ürünün paket bilgisini otomatik çek
    paket_bilgisi = next(item['paket'] for item in urun_katalogu[kat] if item['ad'] == secilen_alt_urun)
    st.info(f"Paketleme Tipi: **{paket_bilgisi}**")
    
    col1, col2 = st.columns(2)
    with col1: fiyat = st.number_input("Satış Birim Fiyatı (TL)", min_value=0.0)
    with col2: miktar = st.number_input("Üretilen Adet", min_value=1)
    
    if st.button("Stoğa İşle"):
        # Veritabanında ürün var mı kontrol et
        c.execute("SELECT id, stok_adet FROM urunler WHERE ad = ? AND paketleme = ?", (secilen_alt_urun, paket_bilgisi))
        row = c.fetchone()
        
        if row:
            yeni_toplam = row[1] + miktar
            c.execute("UPDATE urunler SET stok_adet = ?, birim_fiyat = ? WHERE id = ?", (yeni_toplam, fiyat, row[0]))
        else:
            c.execute("INSERT INTO urunler (ad, kategori, paketleme, birim_fiyat, stok_adet) VALUES (?,?,?,?,?)",
                      (secilen_alt_urun, kat, paket_bilgisi, fiyat, miktar))
        conn.commit()
        st.success(f"{secilen_alt_urun} stokları güncellendi.")

    st.divider()
    st.subheader("Aktüel Ambar Durumu")
    st.dataframe(pd.read_sql_query("SELECT kategori, ad, paketleme, stok_adet as 'Mevcut Adet' FROM urunler", conn), use_container_width=True)

# 2. SATIŞ EKRANI
elif choice == "🛒 Satış Ekranı":
    st.subheader("Yeni Sevkiyat / Satış")
    urunler_df = pd.read_sql_query("SELECT * FROM urunler WHERE stok_adet > 0", conn)
    musteriler_df = pd.read_sql_query("SELECT * FROM musteriler", conn)
    
    if not urunler_df.empty and not musteriler_df.empty:
        with st.form("satis_form"):
            secilen = st.selectbox("Ürün (Stoktakiler)", urunler_df['ad'] + " - " + urunler_df['paketleme'])
            bayi = st.selectbox("Alıcı Bayi", musteriler_df['ad'])
            adet = st.number_input("Satış Adedi", min_value=1)
            tarih = st.date_input("Fatura Tarihi", date.today())
            
            if st.form_submit_button("Satışı Tamamla"):
                u_id = urunler_df.iloc[urunler_df.index[urunler_df['ad'] + " - " + urunler_df['paketleme'] == secilen][0]]['id']
                u_stok = urunler_df.iloc[urunler_df.index[urunler_df['ad'] + " - " + urunler_df['paketleme'] == secilen][0]]['stok_adet']
                u_fiyat = urunler_df.iloc[urunler_df.index[urunler_df['ad'] + " - " + urunler_df['paketleme'] == secilen][0]]['birim_fiyat']
                
                if u_stok >= adet:
                    toplam = adet * u_fiyat
                    c.execute("UPDATE urunler SET stok_adet = ? WHERE id = ?", (u_stok - adet, int(u_id)))
                    m_id = musteriler_df[musteriler_df['ad'] == bayi]['id'].values[0]
                    c.execute("INSERT INTO satislar (tarih, urun_id, musteri_id, adet, toplam_tutar) VALUES (?,?,?,?,?)",
                              (tarih, int(u_id), int(m_id), adet, toplam))
                    conn.commit()
                    st.balloons()
                    st.success(f"Sevkiyat Hazırlandı. Toplam: {toplam} TL")
                else:
                    st.error("Stokta bu kadar ürün yok!")
    else:
        st.warning("Satış yapabilmek için önce stok girişi ve bayi tanımı yapmalısınız.")

# 3. ANALİZ PANELİ (PİVOT)
elif choice == "📈 Analiz Paneli":
    st.subheader("Core Tarım | Pivot Satış Analizi")
    df = pd.read_sql_query("""
        SELECT s.tarih, u.kategori, u.ad as Urun, u.paketleme, m.ad as Bayi, s.adet, s.toplam_tutar 
        FROM satislar s
        JOIN urunler u ON s.urun_id = u.id
        JOIN musteriler m ON s.musteri_id = m.id
    """, conn)
    
    if not df.empty:
        st.markdown("### 📊 Ürün Grubu ve Bayi Bazlı Ciro (Pivot)")
        pivot = df.pivot_table(index=['kategori', 'Urun'], columns='Bayi', values='toplam_tutar', aggfunc='sum', margins=True).fillna(0)
        st.dataframe(pivot.style.format("{:.2f} TL"), use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📦 En Çok Satılan Ürünler (Adet)")
            st.bar_chart(df.groupby('Urun')['adet'].sum())
        with col2:
            st.markdown("### 💰 Bölgesel Ciro Dağılımı")
            st.line_chart(df.groupby('tarih')['toplam_tutar'].sum())
    else:
        st.info("Henüz analiz edilecek satış verisi yok.")

# 4. BAYİ TANIMLAMA
elif choice == "👥 Bayi Tanımlama":
    st.subheader("Yeni Bayi / Müşteri Ekle")
    ad = st.text_input("Bayi Adı")
    bolge = st.selectbox("Bölge", ["İzmir", "İstanbul", "Ankara", "Antalya", "Yurtdışı"])
    if st.button("Kaydet"):
        c.execute("INSERT INTO musteriler (ad, bolge) VALUES (?,?)", (ad, bolge))
        conn.commit()
        st.success(f"{ad} bayisi başarıyla eklendi.")
