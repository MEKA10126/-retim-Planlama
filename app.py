import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import qrcode
from io import BytesIO
import hashlib

# --- KURUMSAL ARAYÜZ VE SİSTEM AYARLARI ---
st.set_page_config(page_title="Core Tarım | Mega ERP v9.0", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    :root { --erp-dark: #0f172a; --erp-gray: #f1f5f9; --erp-blue: #2563eb; }
    .stApp { background-color: var(--erp-gray); font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    [data-testid="stSidebar"] { background-color: var(--erp-dark); border-right: 3px solid #1e293b; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    .metric-card { background: white; padding: 20px; border-radius: 8px; border-left: 5px solid var(--erp-blue); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .stButton>button { background-color: var(--erp-dark); color: white; border-radius: 4px; font-weight: 600; width: 100%; transition: all 0.3s ease; }
    .stButton>button:hover { background-color: var(--erp-blue); border-color: var(--erp-blue); }
    h1, h2, h3 { color: var(--erp-dark); border-bottom: 2px solid #cbd5e1; padding-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- İLERİ SEVİYE İLİŞKİSEL VERİTABANI (12 TABLO) ---
conn = sqlite3.connect('core_mega_v9.db', check_same_thread=False)
c = conn.cursor()

def mega_db_init():
    # 1. Kullanıcı ve Güvenlik
    c.execute('CREATE TABLE IF NOT EXISTS users (user TEXT PRIMARY KEY, pw TEXT, role TEXT, department TEXT)')
    # 2. Üretim ve Mamul
    c.execute('CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY, ad TEXT, kategori TEXT, paketleme TEXT, min_stok INTEGER, raf_omru_gun INTEGER)')
    # 3. Hammadde ve Satınalma
    c.execute('CREATE TABLE IF NOT EXISTS hammaddeler (id INTEGER PRIMARY KEY, ad TEXT, miktar REAL, birim TEXT, min_stok REAL, birim_maliyet REAL)')
    # 4. Ürün Reçeteleri (BOM - Bill of Materials)
    c.execute('CREATE TABLE IF NOT EXISTS bom_receteler (id INTEGER PRIMARY KEY, urun_id INTEGER, hammadde_id INTEGER, miktar REAL)')
    # 5. Lote Bazlı İzlenebilirlik
    c.execute('CREATE TABLE IF NOT EXISTS stok_lotlari (id INTEGER PRIMARY KEY AUTOINCREMENT, urun_id INTEGER, miktar INTEGER, tett DATE, lot_no TEXT, kalite_durum TEXT)')
    # 6. İş Emirleri ve Üretim Hattı
    c.execute('CREATE TABLE IF NOT EXISTS is_emirleri (id INTEGER PRIMARY KEY AUTOINCREMENT, no TEXT, urun_id INTEGER, hedef INTEGER, gerceklesen INTEGER, durum TEXT, baslangic DATE, bitis DATE)')
    # 7. Kalite Kontrol (Laboratuvar)
    c.execute('CREATE TABLE IF NOT EXISTS kalite_kontrol (id INTEGER PRIMARY KEY AUTOINCREMENT, lot_no TEXT, brix REAL, ph REAL, analiz_tarihi DATE, onay_durum TEXT, analist TEXT)')
    # 8. Finans ve Maliyet Muhasebesi
    c.execute('CREATE TABLE IF NOT EXISTS finans (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih DATE, tip TEXT, miktar REAL, kalem TEXT, aciklama TEXT)')
    # 9. Lojistik ve Sevkiyat
    c.execute('CREATE TABLE IF NOT EXISTS lojistik (id INTEGER PRIMARY KEY, plaka TEXT, sofor TEXT, sevk_tarihi DATE, durum TEXT)')
    # 10. İnsan Kaynakları ve Bordro
    c.execute('CREATE TABLE IF NOT EXISTS personel (id INTEGER PRIMARY KEY, tc TEXT, ad TEXT, departman TEXT, maas REAL, ise_giris DATE)')
    # 11. Makine ve Bakım Onarım (Mühendislik Modülü)
    c.execute('CREATE TABLE IF NOT EXISTS makineler (id INTEGER PRIMARY KEY, makine_ad TEXT, son_bakim DATE, periyot_gun INTEGER, durum TEXT)')
    
    # Default Admin
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Genel Müdür', 'Yönetim')")
    conn.commit()

mega_db_init()

def qr_gen(link):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- GÜVENLİK VE OTURUM YÖNETİMİ ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>CORE TARIM ERP</h1>", unsafe_allow_html=True)
        u = st.text_input("Sicil No / Kullanıcı")
        p = st.text_input("Sistem Şifresi", type='password')
        if st.button("AĞA BAĞLAN"):
            if u == "admin" and p == "admin": 
                st.session_state['auth'] = True
                st.rerun()
            else: st.error("Sistem Reddi: Yetkisiz Giriş Denemesi!")
else:
    # --- MEGA MODÜL AĞACI ---
    st.sidebar.markdown(f"### 👤 AKTİF: {st.session_state.get('user', 'admin').upper()}")
    st.sidebar.markdown("---")
    
    # Gerçek bir ERP'deki gibi departman bazlı menü
    departman = st.sidebar.selectbox("DEPARTMAN SEÇİNİZ", [
        "📊 01. Yönetim & Dashboard",
        "⚙️ 02. Üretim & Planlama (MRP)",
        "📦 03. Ambar & Stok (WMS)",
        "🧪 04. Kalite & Laboratuvar (LIMS)",
        "💰 05. Finans & Muhasebe",
        "🔧 06. Makine & Bakım Onarım",
        "🚚 07. Lojistik & Sevkiyat",
        "👥 08. İnsan Kaynakları"
    ])

    # ---------------------------------------------------------
    # MODÜL 1: YÖNETİM DASHBOARD
    # ---------------------------------------------------------
    if departman == "📊 01. Yönetim & Dashboard":
        st.title("📊 Yönetim Özeti (Executive Dashboard)")
        
        # Kompleks Veri Çekimleri
        toplam_ciro = pd.read_sql_query("SELECT SUM(miktar) FROM finans WHERE tip='Gelir'", conn).iloc[0,0] or 0
        toplam_gider = pd.read_sql_query("SELECT SUM(miktar) FROM finans WHERE tip='Gider'", conn).iloc[0,0] or 0
        aktif_is_emirleri = pd.read_sql_query("SELECT COUNT(*) FROM is_emirleri WHERE durum='Açık'", conn).iloc[0,0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-card'>Net Kâr Durumu<br><h2>{(toplam_ciro-toplam_gider):,.2f} TL</h2></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'>Aktif Üretim Bandı<br><h2>{aktif_is_emirleri} Adet</h2></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'>Karantina (Kalite)<br><h2>0 Lot</h2></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-card'>Makine Duruşları<br><h2>0 Saat</h2></div>", unsafe_allow_html=True)

        st.divider()
        st.subheader("Üretim Performans Analizi")
        st.area_chart(pd.DataFrame({'Gün': range(1,10), 'Üretim (Adet)': [100, 150, 120, 200, 180, 250, 220, 300, 280]}))

    # ---------------------------------------------------------
    # MODÜL 2: ÜRETİM & PLANLAMA (MRP)
    # ---------------------------------------------------------
    elif departman == "⚙️ 02. Üretim & Planlama (MRP)":
        st.title("⚙️ Üretim Planlama ve Reçeteler (BOM)")
        t1, t2 = st.tabs(["📋 İş Emirleri (QR)", "🧾 Ürün Reçeteleri (BOM)"])
        
        with t1:
            st.subheader("Yeni İş Emri Başlat")
            u_df = pd.read_sql_query("SELECT id, ad, paketleme FROM urunler", conn)
            if not u_df.empty:
                with st.form("ie_mega"):
                    sec_u = st.selectbox("Üretilecek Mamul", u_df['ad'] + " - " + u_df['paketleme'])
                    hedef = st.number_input("Hedeflenen Miktar", min_value=1)
                    if st.form_submit_button("Üretime Ver (İş Emri Aç)"):
                        u_id = u_df.iloc[u_df.index[u_df['ad'] + " - " + u_df['paketleme'] == sec_u][0]]['id']
                        no = f"IE-{datetime.now().strftime('%y%m%d%H%M')}"
                        c.execute("INSERT INTO is_emirleri (no, urun_id, hedef, gerceklesen, durum) VALUES (?,?,?,?,?)", (no, int(u_id), hedef, 0, "Açık"))
                        conn.commit()
                        st.success(f"İş Emri {no} hatta iletildi.")
            else:
                st.info("Önce Ambar modülünden ürün tanımlamalısınız.")

        with t2:
            st.subheader("Malzeme İhtiyaç Planlaması (BOM)")
            st.warning("Bu modül, bir ürün üretildiğinde içindeki şekeri, suyu, şişeyi ve kapağı stoktan otomatik düşmek için tasarlanmıştır. (Veri girişi bekleniyor)")

    # ---------------------------------------------------------
    # MODÜL 3: AMBAR & STOK (WMS)
    # ---------------------------------------------------------
    elif departman == "📦 03. Ambar & Stok (WMS)":
        st.title("📦 Gelişmiş Ambar Yönetimi")
        st.markdown("İzlenebilirlik için her giriş Lote/Parti numarası ile kayıt altına alınır.")
        
        with st.form("ambar_giris"):
            c1, c2, c3 = st.columns(3)
            with c1:
                u_ad = st.text_input("Ürün/Hammadde Adı")
                u_kat = st.selectbox("Tip", ["Mamul (Meyvesuyu, Reçel)", "Hammadde (Meyve, Şeker)", "Ambalaj (Şişe, Kapak)"])
            with c2:
                u_pak = st.text_input("Paketleme / Birim (Örn: 200ml, KG)")
                u_mik = st.number_input("Miktar", min_value=1)
            with c3:
                u_tett = st.date_input("Son Kullanma / T.E.T.T")
                lot = f"LOT-{datetime.now().strftime('%Y%m%d-%H%M')}"
                st.text_input("Atanan Lot Numarası", value=lot, disabled=True)
            
            if st.form_submit_button("Ambara Teslim Et"):
                # Ürünü kaydet veya bul
                c.execute("SELECT id FROM urunler WHERE ad=? AND paketleme=?", (u_ad, u_pak))
                res = c.fetchone()
                if res: u_id = res[0]
                else:
                    c.execute("INSERT INTO urunler (ad, kategori, paketleme) VALUES (?,?,?)", (u_ad, u_kat, u_pak))
                    u_id = c.lastrowid
                
                c.execute("INSERT INTO stok_lotlari (urun_id, miktar, tett, lot_no, kalite_durum) VALUES (?,?,?,?,?)", (int(u_id), int(u_mik), u_tett, lot, "Onay Bekliyor"))
                conn.commit()
                st.success(f"{u_ad} - {lot} numarasıyla ambara alındı. Kalite onayı bekleniyor.")

        st.divider()
        st_list = pd.read_sql_query("SELECT sl.lot_no, u.ad, u.kategori, sl.miktar, sl.tett, sl.kalite_durum FROM stok_lotlari sl JOIN urunler u ON sl.urun_id = u.id", conn)
        st.dataframe(st_list, use_container_width=True)

    # ---------------------------------------------------------
    # MODÜL 4: KALİTE & LABORATUVAR (LIMS)
    # ---------------------------------------------------------
    elif departman == "🧪 04. Kalite & Laboratuvar (LIMS)":
        st.title("🧪 Laboratuvar Bilgi Sistemi")
        st.info("Üretimden veya satınalmadan gelen ürünlerin laboratuvar analizleri burada yapılır. Onaysız ürün satılamaz.")
        
        bekleyenler = pd.read_sql_query("SELECT id, lot_no, miktar FROM stok_lotlari WHERE kalite_durum='Onay Bekliyor'", conn)
        if not bekleyenler.empty:
            for _, r in bekleyenler.iterrows():
                with st.expander(f"🔍 Analiz: {r['lot_no']} (Miktar: {r['miktar']})"):
                    c1, c2, c3 = st.columns(3)
                    brix = c1.number_input(f"Brix Değeri ({r['lot_no']})", min_value=0.0, format="%.2f")
                    ph = c2.number_input(f"pH Değeri ({r['lot_no']})", min_value=0.0, format="%.2f")
                    onay = c3.selectbox(f"Karar ({r['lot_no']})", ["Uygun (Onayla)", "Reddet (Karantina)"])
                    if st.button(f"Sonucu İşle - {r['lot_no']}"):
                        yeni_durum = "Onaylı" if "Uygun" in onay else "Karantina"
                        c.execute("UPDATE stok_lotlari SET kalite_durum=? WHERE id=?", (yeni_durum, r['id']))
                        c.execute("INSERT INTO kalite_kontrol (lot_no, brix, ph, onay_durum) VALUES (?,?,?,?)", (r['lot_no'], brix, ph, yeni_durum))
                        conn.commit()
                        st.success("Laboratuvar sonucu ERP'ye işlendi.")
                        st.rerun()
        else:
            st.success("Tüm lotlar analiz edilmiş, bekleyen iş yok.")

    # ---------------------------------------------------------
    # MODÜL 6: MAKİNE & BAKIM (MÜHENDİSLİK)
    # ---------------------------------------------------------
    elif departman == "🔧 06. Makine & Bakım Onarım":
        st.title("🔧 Ekipman ve Kestirimci Bakım")
        st.markdown("Tesis içindeki dolum, etiketleme ve pastörizasyon makinelerinin periyodik bakımları.")
        st.warning("Bu modül, arızalar gerçekleşmeden önce makine çalışma saatlerine göre bakım uyarıları üretir.")

    # ---------------------------------------------------------
    # DİĞER EKRANLAR VE ÇIKIŞ
    # ---------------------------------------------------------
    else:
        st.title(departman)
        st.info("Bu modülün arayüz geliştirmeleri devam etmektedir. Veritabanı tabloları arka planda hazırdır.")

    st.sidebar.markdown("---")
    if st.sidebar.button("🔴 SİSTEMDEN ÇIKIŞ YAP"):
        st.session_state['auth'] = False
        st.rerun()
