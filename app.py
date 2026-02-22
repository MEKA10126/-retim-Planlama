import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import qrcode
from io import BytesIO

# --- PROFESYONEL NETSIS TEMASI ---
st.set_page_config(page_title="Core Tarım | Netsis Pro v8.4", layout="wide")

st.markdown("""
    <style>
    :root { --main-bg: #f8fafc; --sidebar-bg: #1e293b; --netsis-blue: #0f172a; }
    .stApp { background-color: var(--main-bg); }
    [data-testid="stSidebar"] { background-color: var(--sidebar-bg); border-right: 2px solid #334155; }
    [data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    .stButton>button { 
        background-color: #334155; color: white; border-radius: 2px; 
        border: 1px solid #1e293b; width: 100%; font-weight: bold; 
    }
    .stMetric { background: white; padding: 15px; border-radius: 5px; border: 1px solid #e2e8f0; }
    h1, h2, h3 { color: var(--netsis-blue); border-bottom: 1px solid #cbd5e1; padding-bottom: 8px; font-family: sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# Veritabanı Onarımı ve Bağlantı
conn = sqlite3.connect('core_netsis_v84.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY, ad TEXT, kategori TEXT, paketleme TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS stok_lotlari (id INTEGER PRIMARY KEY AUTOINCREMENT, urun_id INTEGER, miktar INTEGER, tett DATE)')
    c.execute('CREATE TABLE IF NOT EXISTS is_emirleri (id INTEGER PRIMARY KEY AUTOINCREMENT, no TEXT, urun_id INTEGER, hedef INTEGER, durum TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finans (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih DATE, tip TEXT, miktar REAL, kalem TEXT)')
    conn.commit()

init_db()

# Ürün Kataloğu
urun_katalogu = {
    "Meyve Suyu Grubu": [{"ad": "Nar Suyu", "paket": "200 ml"}, {"ad": "Limonata", "paket": "200 ml"}],
    "Reçel Grubu": [{"ad": "Kivi Reçeli", "paket": "375 g"}, {"ad": "İncir Reçeli", "paket": "375 g"}],
    "Domates Grubu": [{"ad": "Domates Suyu", "paket": "1000 ml"}, {"ad": "Domates Rendesi", "paket": "500 g"}],
    "Ege Otları & Kapari": [{"ad": "Kapari Meyvesi", "paket": "700 g"}, {"ad": "Kapari", "paket": "190 g"}]
}

def qr_gen(link):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- GÜVENLİ GİRİŞ SİSTEMİ ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>SİSTEM GİRİŞİ</h2>", unsafe_allow_html=True)
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type='password')
        if st.button("SİSTEME BAĞLAN"):
            if u == "admin" and p == "admin": 
                st.session_state['auth'] = True
                st.rerun()
            else: st.error("Yetkisiz Erişim! admin/admin bilgilerini kullanın.")
else:
    st.sidebar.markdown("### 🖥️ ERP MODÜLLERİ")
    modul = st.sidebar.radio("", ["🏠 Dashboard", "🏭 İş Emirleri (QR)", "📦 Ambar Yönetimi", "💰 Finans Yönetimi"])

    # 1. DASHBOARD
    if modul == "🏠 Dashboard":
        st.title("📌 Kurumsal Performans Özeti")
        gelir = pd.read_sql_query("SELECT SUM(miktar) FROM finans WHERE tip='Gelir'", conn).iloc[0,0] or 0
        gider = pd.read_sql_query("SELECT SUM(miktar) FROM finans WHERE tip='Gider'", conn).iloc[0,0] or 0
        stok_toplam = pd.read_sql_query("SELECT SUM(miktar) FROM stok_lotlari", conn).iloc[0,0] or 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam Ciro", f"{gelir:,.2f} TL")
        c2.metric("Toplam Gider", f"{gider:,.2f} TL")
        c3.metric("Net Kâr", f"{(gelir-gider):,.2f} TL")
        c4.metric("Ambar Bakiyesi", f"{stok_toplam} Adet")

    # 2. ÜRETİM / İŞ EMİRLERİ
    elif modul == "🏭 İş Emirleri (QR)":
        st.title("🏭 Üretim Planlama")
        with st.form("ie_form"):
            g = st.selectbox("Grup", list(urun_katalogu.keys()))
            s = st.selectbox("Ürün", [u['ad'] for u in urun_katalogu[g]])
            h = st.number_input("Hedef", min_value=1)
            if st.form_submit_button("İş Emri Yayınla"):
                p = next(u['paket'] for u in urun_katalogu[g] if u['ad'] == s)
                c.execute("SELECT id FROM urunler WHERE ad = ? AND paketleme = ?", (s, p))
                res = c.fetchone()
                if res: u_id = res[0]
                else:
                    c.execute("INSERT INTO urunler (ad, kategori, paketleme) VALUES (?,?,?)", (s, g, p))
                    u_id = c.lastrowid
                no = f"IE-{datetime.now().strftime('%d%H%M')}"
                c.execute("INSERT INTO is_emirleri (no, urun_id, hedef, durum) VALUES (?,?,?,?)", (no, int(u_id), h, "Açık"))
                conn.commit()
                st.success(f"İş Emri {no} Oluşturuldu!")

    # 3. AMBAR YÖNETİMİ (ERROR FIX)
    elif modul == "📦 Ambar Yönetimi":
        st.title("📦 Ambar ve Stok Girişi")
        with st.expander("➕ Mevcut Ürün Girişi (Devir)", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                g_m = st.selectbox("Grup Seç", list(urun_katalogu.keys()))
                s_m = st.selectbox("Ürün Seç", [u['ad'] for u in urun_katalogu[g_m]])
            with col2:
                m_m = st.number_input("Miktar", min_value=1)
                t_m = st.date_input("T.E.T.T.", date.today() + timedelta(days=180))
            if st.button("AMBARA EKLE"):
                p_m = next(u['paket'] for u in urun_katalogu[g_m] if u['ad'] == s_m)
                c.execute("SELECT id FROM urunler WHERE ad = ? AND paketleme = ?", (s_m, p_m))
                u_row = c.fetchone()
                if u_row: u_id_final = u_row[0]
                else:
                    c.execute("INSERT INTO urunler (ad, kategori, paketleme) VALUES (?,?,?)", (s_m, g_m, p_m))
                    u_id_final = c.lastrowid
                # Fix: u_id_final'in int olduğundan emin olunuyor
                c.execute("INSERT INTO stok_lotlari (urun_id, miktar, tett) VALUES (?,?,?)", (int(u_id_final), int(m_m), t_m))
                conn.commit()
                st.success("Stok Başarıyla Eklendi!")

        st.subheader("📋 Stok Listesi")
        st_list = pd.read_sql_query("SELECT sl.id, u.ad, u.paketleme, sl.miktar, sl.tett FROM stok_lotlari sl JOIN urunler u ON sl.urun_id = u.id", conn)
        st.dataframe(st_list, use_container_width=True)

    # 4. FİNANS
    elif modul == "💰 Finans Yönetimi":
        st.title("💰 Muhasebe Kayıtları")
        with st.form("finans_form"):
            t = st.selectbox("Tip", ["Gelir", "Gider"])
            k = st.selectbox("Kalem", ["Satış", "İşçilik", "Hammadde", "Enerji"])
            m = st.number_input("Tutar (TL)", min_value=1.0)
            if st.form_submit_button("KAYDET"):
                c.execute("INSERT INTO finans (tarih, tip, miktar, kalem) VALUES (?,?,?,?)", (date.today(), t, m, k))
                conn.commit()
                st.success("Kayıt Alındı.")

    if st.sidebar.button("🔴 OTURUMU KAPAT"):
        st.session_state['auth'] = False
        st.rerun()
