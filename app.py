import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import requests
import ast

st.set_page_config(page_title="GPX Game Office", layout="wide")

# --- KONEKSI ---
try:
    conn = st.connection("supabase", type=SupabaseConnection, 
                         url=st.secrets["SUPABASE_URL"], 
                         key=st.secrets["SUPABASE_KEY"])
    DISCORD_WEBHOOK_URL = st.secrets["MY_WEBHOOK_URL"]
except:
    st.error("Gagal koneksi database!"); st.stop()

# Cache data agar web kencang
@st.cache_data(ttl=5)
def load_data(table_name):
    try:
        return conn.table(table_name).select("*").execute().data
    except: return []

members = load_data("members_data")
prices = load_data("price_data")
stok_gdg = load_data("stok_gudang")
bibit_gdg = load_data("stock_data")

menu = st.sidebar.radio("Menu:", ["📊 Dashboard", "📝 Setoran & Bibit", "✅ Admin Approval", "💰 Pengaturan"])

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring GPX")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📦 Stok Hasil Panen")
        for i in stok_gdg: st.write(f"- {i['item']}: {i['stok']:,} Unit")
    with c2:
        st.subheader("🌱 Stok Bibit Gudang")
        for i in bibit_gdg: st.write(f"- {i['item']}: {i['qty']:,} Pcs")
    
    st.divider()
    st.subheader("🏆 Status Bibit Member")
    if members:
        df_m = pd.DataFrame(members)
        # Menampilkan berapa bibit yang saat ini dibawa member
        st.table(df_m[['nama', 'total_terima', 'total_kembali', 'total_uang']].rename(
            columns={'total_terima': 'Bibit di Tangan', 'total_kembali': 'Total Setoran (Unit)'}
        ))

# --- MENU: SETORAN & BIBIT ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan")
    m_name = st.selectbox("Pilih Member:", [m['nama'] for m in members] if members else ["Belum ada member"])
    t1, t2 = st.tabs(["🍀 Setor Panen", "🌱 Kelola Bibit"])
    
    with t1:
        # (Logika Setor Panen tetap sama)
        st.write("Input hasil panen...")

    with t2:
        st.subheader("Ambil atau Kembalikan Bibit")
        opsi_bibit = st.radio("Aksi:", ["Ambil dari Gudang", "Kembalikan ke Gudang"])
        b_pilih = st.selectbox("Jenis Bibit:", [b['item'] for b in bibit_gdg])
        b_qty = st.number_input("Jumlah Pcs:", min_value=0, step=1)
        
        if st.button("Kirim Laporan Bibit 🚀"):
            tipe_task = "AMBIL_BIBIT" if opsi_bibit == "Ambil dari Gudang" else "RETUR_BIBIT"
            conn.table("pending_tasks").insert({
                "user_nama": m_name, 
                "tipe": tipe_task, 
                "detail": str({b_pilih: b_qty}),
                "total_nominal": 0
            }).execute()
            
            icon = "🌱" if tipe_task == "AMBIL_BIBIT" else "🔄"
            requests.post(DISCORD_WEBHOOK_URL, json={"content": f"{icon} **{tipe_task}**: {m_name} | {b_pilih}: {b_qty} Pcs"})
            st.success(f"Laporan {opsi_bibit} Berhasil!")

# --- MENU: APPROVAL (Logika Joe) ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    tasks = conn.table("pending_tasks").select("*").eq("status", "Pending").execute().data
    if not tasks: st.info("Tidak ada antrean.")
    else:
        for t in tasks:
            with st.expander(f"📌 {t['user_nama']} - {t['tipe']}"):
                st.write(f"Detail: {t['detail']}")
                if st.button("APPROVE ✅", key=f"bt_{t['id']}"):
                    det = ast.literal_eval(t['detail'])
                    m_data = next(m for m in members if m['nama'] == t['user_nama'])
                    
                    if t['tipe'] == "AMBIL_BIBIT":
                        for it, q in det.items():
                            # Gudang berkurang, Member bertambah
                            b_data = next(b for b in bibit_gdg if b['item'] == it)
                            conn.table("stock_data").update({"qty": b_data['qty'] - q}).eq("item", it).execute()
                            conn.table("members_data").update({"total_terima": m_data['total_terima'] + q}).eq("nama", t['user_nama']).execute()
                    
                    elif t['tipe'] == "RETUR_BIBIT":
                        for it, q in det.items():
                            # Gudang bertambah, Member berkurang (Logika Joe)
                            b_data = next(b for b in bibit_gdg if b['item'] == it)
                            conn.table("stock_data").update({"qty": b_data['qty'] + q}).eq("item", it).execute()
                            conn.table("members_data").update({"total_terima": m_data['total_terima'] - q}).eq("nama", t['user_nama']).execute()
                    
                    # (Logika Approval SETOR tetap sama)
                    
                    conn.table("pending_tasks").update({"status": "Approved"}).eq("id", t['id']).execute()
                    st.cache_data.clear(); st.rerun()

# --- MENU: PENGATURAN ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan")
    # (Sama seperti sebelumnya: Editor Member, Harga, dan Stok Bibit)
