import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import qrcode
from io import BytesIO

# --- KURUMSAL TEMA ---
st.set_page_config(page_title="Core Tarım | Finans & Stok", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    [data-testid="stSidebar"] { background-color: #0c4a6e; }
    .stButton>button { background-color: #0284c7; color: white; border-radius: 8px; font-weight: bold; }
    .finance-card { background-color: #e2e8f0; padding: 15px; border-radius: 10px; border-left: 5px solid #64748b; }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı Bağlantısı
conn = sqlite3.connect('core_tarim_v7.db', check_same_thread=False)
c = conn.cursor()

# Tabloları Güncelle (Giderler Tablosu Eklendi)
c.execute('CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY, ad TEXT, kategori TEXT, paketleme TEXT, birim_fiyat REAL)')
c.execute('CREATE TABLE IF NOT EXISTS stok_lotlari (id INTEGER PRIMARY KEY AUTOINCREMENT, urun_id INTEGER, miktar INTEGER, tett DATE)')
c.execute('CREATE TABLE IF NOT EXISTS is_emirleri (id INTEGER PRIMARY KEY AUTOINCREMENT, is_emri_no TEXT, urun_id INTEGER, hedef_miktar INTEGER, durum TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS satislar (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih DATE, urun_id INTEGER, adet INTEGER, tutar REAL)')
c.execute('CREATE TABLE IF NOT EXISTS giderler (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih DATE, tip TEXT, miktar REAL, aciklama TEXT)')
conn.commit()

# --- ARAYÜZ ---
params = st.query_params
if "is_emri" in params:
    choice = "QR Personel Paneli"
else:
    choice = st.sidebar.selectbox("Yönetim Menüsü", [
        "💰 Finansal Özet & Kâr/Zarar", 
        "💸 Gider Girişi",
        "📦 Ambar & Mevcut Ürün Girişi", 
        "📋 İş Emirleri",
        "🛒 Satış Kaydı"
    ])

# 1. FİNANSAL ÖZET (Yeni Analiz Sistemi)
if choice == "💰 Finansal Özet & Kâr/Zarar":
    st.header("💰 Finansal Performans Analizi")
    
    # Verileri Çek
    gelir_df = pd.read_sql_query("SELECT SUM(tutar) as toplam FROM satislar", conn)
    gider_df = pd.read_sql_query("SELECT tip, SUM(miktar) as miktar FROM giderler GROUP BY tip", conn)
    toplam_gelir = gelir_df['toplam'].iloc[0] or 0
    toplam_gider = gider_df['miktar'].sum() or 0
    net_kar = toplam_gelir - toplam_gider

    # Üst Göstergeler
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Ciro", f"{toplam_gelir:,.2f} TL")
    col2.metric("Toplam Gider", f"{toplam_gider:,.2f} TL", delta_color="inverse")
    col3.metric("Net Kâr", f"{net_kar:,.2f} TL", delta=f"{(net_kar/toplam_gelir*100 if toplam_gelir > 0 else 0):.1f}%")

    st.divider()
    
    # Gider Dağılımı ve Pivot
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("📊 Gider Kırılımı")
        if not gider_df.empty:
            st.dataframe(gider_df, use_container_width=True)
        else:
            st.info("Henüz gider kaydı yok.")
    with c2:
        st.subheader("📈 Gelir/Gider Dengesi")
        chart_data = pd.DataFrame({
            'Kategori': ['Gelir', 'Gider'],
            'Miktar': [toplam_gelir, toplam_gider]
        })
        st.bar_chart(data=chart_data, x='Kategori', y='Miktar')

# 2. GİDER GİRİŞİ (Yeni Modül)
elif choice == "💸 Gider Girişi":
    st.header("💸 Operasyonel Gider Girişi")
    
    with st.form("gider_form"):
        col1, col2 = st.columns(2)
        with col1:
            gider_tipi = st.selectbox("Gider Kalemi", [
                "İşçi Maaşları", "Elektrik", "Su / Doğalgaz", 
                "Hammadde Alımı", "Ambalaj Malzemesi", 
                "Nakliye / Lojistik", "Pazarlama", "Diğer"
            ])
            gider_tarih = st.date_input("Gider Tarihi", date.today())
        with col2:
            gider_miktar = st.number_input("Tutar (TL)", min_value=0.0)
            gider_not = st.text_area("Açıklama (Opsiyonel)")
        
        if st.form_submit_button("Gideri Kaydet"):
            c.execute("INSERT INTO giderler (tarih, tip, miktar, aciklama) VALUES (?,?,?,?)",
                      (gider_tarih, gider_tipi, gider_miktar, gider_not))
            conn.commit()
            st.success(f"{gider_tipi} gideri başarıyla işlendi.")

# 5. SATIŞ KAYDI (Kâr hesabı için gerekli)
elif choice == "🛒 Satış Kaydı":
    st.header("🛒 Sevkiyat ve Satış Kaydı")
    urunler_df = pd.read_sql_query("SELECT id, ad, paketleme FROM urunler", conn)
    
    with st.form("satis_form"):
        secilen_u = st.selectbox("Ürün", urunler_df['ad'] + " - " + urunler_df['paketleme'])
        s_adet = st.number_input("Satış Adedi", min_value=1)
        s_fiyat = st.number_input("Birim Satış Fiyatı (TL)", min_value=0.0)
        s_tarih = st.date_input("Satış Tarihi", date.today())
        
        if st.form_submit_button("Satışı Onayla"):
            u_id = urunler_df.iloc[urunler_df.index[urunler_df['ad'] + " - " + urunler_df['paketleme'] == secilen_u][0]]['id']
            toplam = s_adet * s_fiyat
            c.execute("INSERT INTO satislar (tarih, urun_id, adet, tutar) VALUES (?,?,?,?)",
                      (s_tarih, int(u_id), s_adet, toplam))
            conn.commit()
            st.success(f"Satış Kaydedildi: {toplam} TL")

# --- DİĞER MODÜLLER (Ambar ve İş Emri kodları v7.1 ile aynıdır) ---
