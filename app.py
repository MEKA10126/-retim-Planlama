import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import qrcode
from io import BytesIO
from PIL import Image

# --- KURUMSAL TEMA VE QR AYARLARI ---
st.set_page_config(page_title="Core Tarım | İş Emri & QR", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #0c4a6e; }
    .stButton>button { background-color: #0284c7; color: white; border-radius: 8px; font-weight: bold; }
    .qr-box { border: 2px dashed #0284c7; padding: 10px; text-align: center; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı Bağlantısı
conn = sqlite3.connect('core_tarim_v6.db', check_same_thread=False)
c = conn.cursor()

# Tabloları Güncelle (Is Emri Tablosu Eklendi)
c.execute('CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY, ad TEXT, paketleme TEXT, birim_fiyat REAL, stok_adet INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS musteriler (id INTEGER PRIMARY KEY, ad TEXT, bolge TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS satislar (id INTEGER PRIMARY KEY, tarih DATE, urun_id INTEGER, miktar INTEGER, tutar REAL)')
c.execute('''CREATE TABLE IF NOT EXISTS is_emirleri 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, is_emri_no TEXT, urun_id INTEGER, hedef_miktar INTEGER, durum TEXT)''')
conn.commit()

# --- FONKSİYONLAR ---
def qr_olustur(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- ARAYÜZ ---
st.sidebar.title("Core Tarım Kontrol")
# QR ile giriş simülasyonu için URL parametresi kontrolü
query_params = st.query_params
if "is_emri" in query_params:
    choice = "QR İşlem Ekranı"
else:
    choice = st.sidebar.selectbox("Modül Seçiniz", ["📊 Analiz Paneli", "📋 İş Emirleri Yönetimi", "🛒 Satış & Sevkiyat", "📦 Genel Stok"])

# --- MODÜLLER ---

# 1. İŞ EMİRLERİ YÖNETİMİ (Yönetici Ekranı)
if choice == "📋 İş Emirleri Yönetimi":
    st.header("📋 İş Emri Oluşturma ve Takip")
    
    with st.expander("➕ Yeni İş Emri Oluştur"):
        urunler_df = pd.read_sql_query("SELECT id, ad, paketleme FROM urunler", conn)
        is_emri_no = st.text_input("İş Emri Numarası", f"IE-{datetime.now().strftime('%m%d%H%M')}")
        secilen_urun_bilgi = st.selectbox("Üretilecek Ürün", urunler_df['ad'] + " (" + urunler_df['paketleme'] + ")")
        hedef = st.number_input("Hedef Üretim Miktarı (Adet)", min_value=1)
        
        if st.button("İş Emrini Yayınla"):
            u_id = urunler_df.iloc[urunler_df.index[urunler_df['ad'] + " (" + urunler_df['paketleme'] + ")" == secilen_urun_bilgi][0]]['id']
            c.execute("INSERT INTO is_emirleri (is_emri_no, urun_id, hedef_miktar, durum) VALUES (?,?,?,?)",
                      (is_emri_no, int(u_id), hedef, "Açık"))
            conn.commit()
            st.success(f"İş Emri {is_emri_no} başarıyla oluşturuldu!")

    st.subheader("Aktif İş Emirleri ve QR Kodlar")
    emirler = pd.read_sql_query("""
        SELECT ie.id, ie.is_emri_no, u.ad, u.paketleme, ie.hedef_miktar, ie.durum 
        FROM is_emirleri ie JOIN urunler u ON ie.urun_id = u.id WHERE ie.durum = 'Açık'
    """, conn)
    
    for index, row in emirler.iterrows():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**No:** {row['is_emri_no']} | **Ürün:** {row['ad']} | **Hedef:** {row['hedef_miktar']} Adet")
        with col2:
            # QR Kod Linki Oluşturma (Localhost yerine canlı URL'nizi buraya yazabilirsiniz)
            app_url = "https://your-app-link.streamlit.app" # BURAYA KENDİ LİNKİNİZİ GELECEK
            qr_link = f"{app_url}/?is_emri={row['id']}"
            qr_img = qr_olustur(qr_link)
            st.image(qr_img, width=100)
            st.download_button(f"QR İndir ({row['is_emri_no']})", qr_img, file_name=f"qr_{row['is_emri_no']}.png")
        st.divider()

# 2. QR İŞLEM EKRANI (Personel Ekranı)
elif choice == "QR İşlem Ekranı":
    emre_id = query_params["is_emri"]
    st.header("⚡ Hızlı Stok İşlemi")
    
    emir_detay = pd.read_sql_query(f"""
        SELECT ie.*, u.ad, u.stok_adet, u.paketleme FROM is_emirleri ie 
        JOIN urunler u ON ie.urun_id = u.id WHERE ie.id = {emre_id}
    """, conn).iloc[0]
    
    st.metric("İş Emri", emir_detay['is_emri_no'])
    st.metric("Ürün", f"{emir_detay['ad']} ({emir_detay['paketleme']})")
    st.write(f"**Mevcut Stok:** {emir_detay['stok_adet']}")
    
    islem_miktari = st.number_input("İşlem Miktarı (Adet)", min_value=1)
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ STOĞA EKLE"):
            yeni_stok = emir_detay['stok_adet'] + islem_miktari
            c.execute("UPDATE urunler SET stok_adet = ? WHERE id = ?", (yeni_stok, int(emir_detay['urun_id'])))
            conn.commit()
            st.success("Stok Başarıyla Artırıldı!")
            st.rerun()
    with c2:
        if st.button("➖ STOKTAN DÜŞ"):
            if emir_detay['stok_adet'] >= islem_miktari:
                yeni_stok = emir_detay['stok_adet'] - islem_miktari
                c.execute("UPDATE urunler SET stok_adet = ? WHERE id = ?", (yeni_stok, int(emir_detay['urun_id'])))
                conn.commit()
                st.warning("Stoktan Düşüldü!")
                st.rerun()
            else:
                st.error("Yetersiz Stok!")

# 3. GENEL STOK (Ürün Kartı Açmak İçin)
elif choice == "📦 Genel Stok":
    st.header("📦 Genel Ürün ve Stok Listesi")
    # (Buraya önceki sürümlerdeki ürün ekleme ve listeleme kodlarını ekleyebilirsiniz)
    st.write("Buradan manuel stok takibi yapabilirsiniz.")
    df_stok = pd.read_sql_query("SELECT * FROM urunler", conn)
    st.dataframe(df_stok, use_container_width=True)

# 4. ANALİZ VE SATIŞ (Önceki Fonksiyonlar)
else:
    st.info("Lütfen bir modül seçin veya QR kod okutun.")
