import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import requests
import ast

st.set_page_config(page_title="GPX Game Office", layout="wide", page_icon="🏢")

# --- KONEKSI ---
try:
    conn = st.connection("supabase", type=SupabaseConnection, 
                         url=st.secrets["SUPABASE_URL"], 
                         key=st.secrets["SUPABASE_KEY"])
    DISCORD_WEBHOOK_URL = st.secrets["MY_WEBHOOK_URL"]
except:
    st.error("Koneksi gagal! Cek Secrets."); st.stop()

# --- LOAD DATA ---
def load_all_data():
    try:
        m = conn.table("members_data").select("*").execute()
        s = conn.table("stok_gudang").select("*").execute()
        p = conn.table("price_data").select("*").execute()
        b = conn.table("stock_data").select("*").execute() # Data Bibit
        return m.data, s.data, p.data, b.data
    except:
        return [], [], [], []

members_data, stok_data, price_data, bibit_data = load_all_data()

# --- MENU ---
menu = st.sidebar.radio("Navigasi:", ["📊 Dashboard", "📝 Setoran & Bibit", "✅ Admin Approval", "💰 Pengaturan"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring Dashboard GPX")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📦 Stok Hasil Panen")
        if stok_data:
            cols = st.columns(len(stok_data))
            for i, it in enumerate(stok_data):
                cols[i].metric(it['item'], f"{it['stok']:,} Unit")
    with c2:
        st.subheader("🌱 Stok Bibit Tersedia")
        if bibit_data:
            cols = st.columns(len(bibit_data))
            for i, it in enumerate(bibit_data):
                cols[i].metric(it['item'], f"{it['qty']:,} Pcs")

# --- SETORAN & AMBIL BIBIT ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan Member")
    m_name = st.selectbox("Pilih Member:", sorted([m['nama'] for m in members_data]))
    tab1, tab2 = st.tabs(["🍀 Setoran Panen", "🌱 Ambil Bibit"])
    
    with tab1: # FITUR SETORAN (SUDAH ADA)
        # ... (Logika Setoran Panen yang lama tetap ada di sini)
        st.info("Input jumlah panen untuk disetor.")

    with tab2: # FITUR BARU: AMBIL BIBIT
        st.subheader("Form Pengambilan Bibit")
        if not bibit_data:
            st.warning("Stok bibit di gudang kosong. Admin harus input stok di menu Pengaturan.")
        else:
            bibit_options = {b['item']: b['qty'] for b in bibit_data}
            pilih_bibit = st.selectbox("Jenis Bibit:", list(bibit_options.keys()))
            st.write(f"Stok Tersedia: {bibit_options[pilih_bibit]} Pcs")
            jml_ambil = st.number_input("Jumlah Ambil:", min_value=0, max_value=bibit_options[pilih_bibit], step=1)
            
            if st.button("Kirim Laporan Bibit 🚀"):
                if jml_ambil > 0:
                    conn.table("pending_tasks").insert({
                        "user_nama": m_name, "tipe": "BIBIT", 
                        "detail": str({pilih_bibit: jml_ambil}),
                        "total_nominal": 0, "status": "Pending"
                    }).execute()
                    # Discord Bot
                    msg = f"🌱 **PENGAMBILAN BIBIT**\nMember: **{m_name}**\nBibit: {pilih_bibit}\nJumlah: **{jml_ambil} Pcs**"
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
                    st.success("Laporan pengambilan bibit terkirim!")

# --- APPROVAL (TRACKING OTOMATIS) ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    tasks = conn.table("pending_tasks").select("*").eq("status", "Pending").execute()
    if not tasks.data: st.info("Antrean kosong.")
    else:
        for t in tasks.data:
            with st.expander(f"📌 {t['user_nama']} - {t['tipe']}"):
                st.write(f"Detail: {t['detail']}")
                if st.button("SETUJUI ✅", key=f"app_{t['id']}"):
                    details = ast.literal_eval(t['detail'])
                    if t['tipe'] == "BIBIT":
                        # 1. Potong Stok Bibit Gudang
                        for it, q in details.items():
                            b_curr = next(b for b in bibit_data if b['item'] == it)
                            conn.table("stock_data").update({"qty": int(b_curr['qty']) - q}).eq("item", it).execute()
                        # 2. Catat di Member (Track total bibit yang diterima)
                        m_curr = next(m for m in members_data if m['nama'] == t['user_nama'])
                        conn.table("members_data").update({"total_terima": int(m_curr.get('total_terima', 0)) + sum(details.values())}).eq("nama", t['user_nama']).execute()
                    
                    # (Logika Approval SETORAN tetap sama seperti sebelumnya)
                    
                    conn.table("pending_tasks").update({"status": "Approved"}).eq("id", t['id']).execute()
                    st.rerun()

# --- PENGATURAN (INPUT STOK BIBIT) ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan")
    tab1, tab2, tab3 = st.tabs(["Member", "Harga Panen", "Stok Bibit (Admin)"])
    # ... (Tab Member & Harga tetap sama)
    with tab3:
        st.subheader("Input Stok Bibit Baru")
        df_b = pd.DataFrame(bibit_data) if bibit_data else pd.DataFrame(columns=['item', 'qty'])
        ed_b = st.data_editor(df_b, num_rows="dynamic", key="ed_bibit")
        if st.button("Simpan Stok Bibit"):
            for _, row in ed_b.iterrows():
                conn.table("stock_data").upsert(row.to_dict(), on_conflict="item").execute()
            st.rerun()
