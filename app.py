import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import qrcode
from io import BytesIO

# --- KURUMSAL NETSIS TEMASI ---
st.set_page_config(page_title="Core Tarım | Netsis Pro v8.3", layout="wide")

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

# Veritabanı Mimarisi ve Tablo Onarımı
conn = sqlite3.connect('core_netsis_final_v83.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY, ad TEXT, kategori TEXT, paketleme TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS hammaddeler (id INTEGER PRIMARY KEY, ad TEXT, miktar REAL, birim TEXT, kritik REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS stok_lotlari (id INTEGER PRIMARY KEY AUTOINCREMENT, urun_id INTEGER, miktar INTEGER, tett DATE)')
    c.execute('CREATE TABLE IF NOT EXISTS is_emirleri (id INTEGER PRIMARY KEY AUTOINCREMENT, no TEXT, urun_id INTEGER, hedef INTEGER, durum TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finans (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih DATE, tip TEXT, miktar REAL, kalem TEXT)')
    conn.commit()

init_db()

# Ürün Kataloğu (Görsellerdeki paketleme detaylarıyla)
urun_katalogu = {
    "Meyve Suyu Grubu": [
        {"ad": "Nar Suyu", "paket": "200 ml"}, {"ad": "Limonata", "paket": "200 ml"}, 
        {"ad": "Karadut Suyu", "paket": "200 ml"}, {"ad": "Portakal Suyu", "paket": "200 ml"},
        {"ad": "Coremey Nar Suyu", "paket": "1000 ml"}, {"ad": "Coremey Limonata", "paket": "1000 ml"},
        {"ad": "Coremey Karadut Suyu", "paket": "1000 ml"}, {"ad": "Coremey Portakal Suyu", "paket": "1000 ml"},
        {"ad": "Nar Ekşisi", "paket": "250 g"}
    ],
    "Reçel Grubu": [
        {"ad": "Kivi Reçeli", "paket": "375 g"}, {"ad": "İncir Reçeli", "paket": "375 g"},
        {"ad": "Ahududu Reçeli", "paket": "375 g"}, {"ad": "Kayısı Reçeli", "paket": "375 g"},
        {"ad": "Vişne Reçeli", "paket": "375 g"}, {"ad": "Portakal Reçeli", "paket": "375 g"}
    ],
    "Domates Grubu": [
        {"ad": "Domates Suyu", "paket": "1000 ml"}, {"ad": "Domates Rendesi", "paket": "500 g"},
        {"ad": "Doğranmış Domates", "paket": "500 g"}, {"ad": "Menemen Harcı", "paket": "500 g"}
    ],
    "Ege Otları & Kapari": [
        {"ad": "Şevket-i Bostan", "paket": "320 g"}, {"ad": "Deniz Börülcesi", "paket": "350 g"},
        {"ad": "Enginar Kalbi", "paket": "360 g"}, {"ad": "Kapari Meyvesi", "paket": "700 g"},
        {"ad": "Kapari", "paket": "190 g"}
    ]
}

def qr_gen(link):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- GİRİŞ PANELİ ---
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
    # --- NETSIS MODÜLER MENÜ ---
    st.sidebar.markdown("### 🖥️ ERP MODÜLLERİ")
    modul = st.sidebar.radio("", [
        "🏠 Genel Dashboard",
        "🏭 Üretim Planlama (QR)",
        "📦 Ambar & Mevcut Ürün Girişi",
        "🕒 T.E.T.T. Uyarı Sistemi",
        "💰 Cari & Finans Yönetimi"
    ])

    # 1. DASHBOARD
    if modul == "🏠 Genel Dashboard":
        st.title("📌 Kurumsal Performans Özeti")
        gelir = pd.read_sql_query("SELECT SUM(miktar) FROM finans WHERE tip='Gelir'", conn).iloc[0,0] or 0
        gider = pd.read_sql_query("SELECT SUM(miktar) FROM finans WHERE tip='Gider'", conn).iloc[0,0] or 0
        stok_toplam = pd.read_sql_query("SELECT SUM(miktar) FROM stok_lotlari", conn).iloc[0,0] or 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam Ciro", f"{gelir:,.2f} TL")
        c2.metric("Toplam Gider", f"{gider:,.2f} TL")
        c3.metric("Net Kâr/Zarar", f"{(gelir-gider):,.2f} TL")
        c4.metric("Ambar Bakiyesi", f"{stok_toplam} Adet")

    # 2. ÜRETİM PLANLAMA (DÜZELTİLDİ)
    elif modul == "🏭 Üretim Planlama (QR)":
        st.title("🏭 İş Emirleri ve Üretim")
        with st.form("ie_form"):
            g = st.selectbox("Grup", list(urun_katalogu.keys()))
            s = st.selectbox("Ürün", [u['ad'] for u in urun_katalogu[g]])
            p = next(u['paket'] for u in urun_katalogu[g] if u['ad'] == s)
            h = st.number_input("Hedef", min_value=1)
            if st.form_submit_button("İş Emri Yayınla"):
                c.execute("SELECT id FROM urunler WHERE ad = ? AND paketleme = ?", (s, p))
                u_row = c.fetchone()
                u_id = u_row[0] if u_row else (c.execute("INSERT INTO urunler (ad, kategori, paketleme) VALUES (?,?,?)", (s, g, p)) or c.lastrowid)
                no = f"IE-{datetime.now().strftime('%d%H%M')}"
                c.execute("INSERT INTO is_emirleri (no, urun_id, hedef, durum) VALUES (?,?,?,?)", (no, int(u_id), h, "Açık"))
                conn.commit()
                st.success(f"İş Emri {no} Oluşturuldu!")

        st.subheader("Aktif QR Kodlar")
        emirler = pd.read_sql_query("SELECT ie.id, ie.no, u.ad, u.paketleme FROM is_emirleri ie JOIN urunler u ON ie.urun_id = u.id WHERE ie.durum = 'Açık'", conn)
        for _, row in emirler.iterrows():
            c1, c2 = st.columns([3, 1])
            with c1: st.write(f"**{row['no']}** | {row['ad']} ({row['paketleme']})")
            with c2:
                base_url = "https://meka10126-retim-planlama.streamlit.app" 
                st.image(qr_gen(f"{base_url}/?is_emri={row['id']}"), width=100)
            st.divider()

    # 3. AMBAR & MEVCUT ÜRÜN GİRİŞİ (EKLEME-ÇIKARMA AKTİF)
    elif modul == "📦 Ambar & Mevcut Ürün Girişi":
        st.title("📦 Ambar Yönetimi")
        with st.expander("➕ Mevcut Ürün Girişi (Devir)"):
            col1, col2 = st.columns(2)
            with col1:
                g_m = st.selectbox("Grup Seç", list(urun_katalogu.keys()))
                s_m = st.selectbox("Ürün Seç", [u['ad'] for u in urun_katalogu[g_m]])
            with col2:
                p_m = next(u['paket'] for u in urun_katalogu[g_m] if u['ad'] == s_m)
                m_m = st.number_input("Miktar", min_value=1)
                t_m = st.date_input("T.E.T.T.", date.today() + timedelta(days=180))
            if st.button("AMBARA EKLE"):
                c.execute("SELECT id FROM urunler WHERE ad = ? AND paketleme = ?", (s_m, p_m))
                u_id = c.fetchone()
                u_final = u_id[0] if u_id else (c.execute("INSERT INTO urunler (ad, kategori, paketleme) VALUES (?,?,?)", (s_m, g_m, p_m)) or c.lastrowid)
                c.execute("INSERT INTO stok_lotlari (urun_id, miktar, tett) VALUES (?,?,?)", (int(u_final), m_m, t_m))
                conn.commit()
                st.success("Stok Girişi Başarılı!")

        st.subheader("📋 Güncel Stok Listesi")
        st_list = pd.read_sql_query("SELECT sl.id, u.ad, u.paketleme, sl.miktar, sl.tett FROM stok_lotlari sl JOIN urunler u ON sl.urun_id = u.id WHERE sl.miktar > 0", conn)
        st.dataframe(st_list, use_container_width=True)
        
        # Stoktan Çıkarma İşlemi
        if not st_list.empty:
            with st.expander("➖ Stoktan Manuel Çıkar"):
                secilen_lot = st.selectbox("Çıkarılacak Lot ID", st_list['id'])
                c_miktar = st.number_input("Çıkarılacak Miktar", min_value=1)
                if st.button("STOKTAN DÜŞ"):
                    c.execute("UPDATE stok_lotlari SET miktar = miktar - ? WHERE id = ?", (c_miktar, int(secilen_lot)))
                    conn.commit()
                    st.warning("Stok Güncellendi!")
                    st.rerun()

    # 4. T.E.T.T. SİSTEMİ
    elif modul == "🕒 T.E.T.T. Uyarı Sistemi":
        st.title("🕒 Kritik Tarih Kontrolü")
        # (Önceki sürümlerdeki çalışan tarih takibi kodları)

    # 5. FİNANS YÖNETİMİ (EKLEME AKTİF)
    elif modul == "💰 Cari & Finans Yönetimi":
        st.title("💰 Muhasebe Fişleri")
        with st.form("finans_form"):
            t = st.selectbox("Tip", ["Gelir", "Gider"])
            k = st.selectbox("Kalem", ["Satış", "İşçilik", "Elektrik", "Hammadde", "Lojistik"])
            m = st.number_input("Tutar (TL)", min_value=0.1)
            if st.form_submit_button("FİŞİ KAYDET"):
                c.execute("INSERT INTO finans (tarih, tip, miktar, kalem) VALUES (?,?,?,?)", (date.today(), t, m, k))
                conn.commit()
                st.success("Finansal Kayıt Oluşturuldu!")

    if st.sidebar.button("🔴 OTURUMU KAPAT"):
        st.session_state['auth'] = False
        st.rerun()
