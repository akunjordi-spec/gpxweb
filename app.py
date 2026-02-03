import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import requests
import ast

st.set_page_config(page_title="GPX Game Office", layout="wide", page_icon="🏢")

# --- KONEKSI DATABASE ---
try:
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["SUPABASE_URL"],
        key=st.secrets["SUPABASE_KEY"]
    )
    DISCORD_WEBHOOK_URL = st.secrets["MY_WEBHOOK_URL"]
except Exception as e:
    st.error(f"❌ Koneksi Gagal: {e}")
    st.stop()

# --- FUNGSI LOAD DATA ---
def load_all_data():
    try:
        m = conn.table("members_data").select("*").execute()
        s = conn.table("stok_gudang").select("*").execute()
        b = conn.table("stock_data").select("*").execute()
        p = conn.table("price_data").select("*").execute()
        return m.data, s.data, b.data, p.data
    except:
        return [], [], [], []

members_data, stok_data, bibit_data, price_data = load_all_data()

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("🏢 MENU UTAMA")
menu = st.sidebar.radio("Navigasi:", ["📊 Dashboard", "📝 Setoran & Bibit", "✅ Admin Approval", "💰 Pengaturan"])

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring Dashboard GPX")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📦 Stok Gudang")
        if stok_data:
            cols = st.columns(len(stok_data))
            for i, item in enumerate(stok_data):
                cols[i].metric(item['item'], f"{item['stok']:,}")
    with c2:
        st.subheader("🌱 Stok Bibit")
        if bibit_data:
            cols = st.columns(len(bibit_data))
            for i, item in enumerate(bibit_data):
                cols[i].metric(item['item'], f"{item['qty']:,}")
    
    st.divider()
    st.subheader("🏆 Leaderboard Penyetor Terajin (Unit Fisik)")
    if members_data:
        df_m = pd.DataFrame(members_data)
        top_phys = df_m.nlargest(10, 'total_kembali')[['nama', 'total_kembali', 'total_uang']]
        st.table(top_phys.rename(columns={'nama': 'Nama Member', 'total_kembali': 'Total Unit', 'total_uang': 'Saldo Rp'}))

# --- MENU: SETORAN & BIBIT ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan Member")
    if not members_data or not price_data:
        st.warning("⚠️ Data Member atau Harga belum diatur. Silakan ke menu **Pengaturan** dulu!")
    else:
        m_name = st.selectbox("Pilih Member:", sorted([m['nama'] for m in members_data]))
        t1, t2 = st.tabs(["🍀 Setoran Panen", "🌱 Ambil Bibit"])
        with t1:
            prices = {p['item']: p['price'] for p in price_data}
            input_data, total_rp, rincian_msg = {}, 0, []
            cols = st.columns(3)
            for i, (item, harga) in enumerate(prices.items()):
                qty = cols[i % 3].number_input(f"{item} (Rp{harga:,})", min_value=0, step=1, key=f"s_{item}")
                if qty > 0:
                    input_data[item] = qty
                    total_rp += (qty * harga)
                    rincian_msg.append(f"{item} : {qty:,}")
            if st.button("Kirim Laporan 🚀"):
                if input_data:
                    conn.table("pending_tasks").insert({"user_nama": m_name, "tipe": "SETOR", "detail": str(input_data), "total_nominal": total_rp, "status": "Pending"}).execute()
                    msg = f"**SETORAN {datetime.now().strftime('%d/%m/%y')}**\n\n**{m_name}**\n" + "\n".join(rincian_msg) + f"\n**TOTAL : {total_rp:,}**"
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
                    st.success("Terkirim! Menunggu konfirmasi.")

# --- MENU: ADMIN APPROVAL ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    try:
        tasks = conn.table("pending_tasks").select("*").eq("status", "Pending").execute()
        if not tasks.data:
            st.info("Tidak ada antrean laporan.")
        else:
            for t in tasks.data:
                with st.expander(f"📌 {t['user_nama']} - {t['tipe']} - Rp{t['total_nominal']:,}"):
                    st.write(f"Rincian: {t['detail']}")
                    if st.button("SETUJUI ✅", key=f"app_{t['id']}"):
                        if t['tipe'] == "SETOR":
                            details = ast.literal_eval(t['detail'])
                            m_curr = next(m for m in members_data if m['nama'] == t['user_nama'])
                            conn.table("members_data").update({"total_uang": int(m_curr['total_uang']) + int(t['total_nominal']), "total_kembali": int(m_curr['total_kembali']) + sum(details.values())}).eq("nama", t['user_nama']).execute()
                            for it, q in details.items():
                                s_curr = next(s for s in stok_data if s['item'] == it)
                                conn.table("stok_gudang").update({"stok": int(s_curr['stok']) + q}).eq("item", it).execute()
                        conn.table("pending_tasks").update({"status": "Approved"}).eq("id", t['id']).execute()
                        st.rerun()
    except:
        st.error("Gagal memuat antrean. Pastikan tabel pending_tasks sudah dibuat.")

# --- MENU: PENGATURAN (UNTUK EDIT NAMA & HARGA) ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan Pusat")
    tab_m, tab_h = st.tabs(["👥 Manajemen Member", "💵 Manajemen Harga & Barang"])
    with tab_m:
        st.subheader("Daftar Member (Edit Nama/Tambah)")
        df_m = pd.DataFrame(members_data) if members_data else pd.DataFrame(columns=['nama', 'total_terima', 'total_kembali', 'total_uang'])
        ed_m = st.data_editor(df_m, num_rows="dynamic", key="ed_m")
        if st.button("Simpan Member"):
            for _, row in ed_m.iterrows():
                conn.table("members_data").upsert(row.to_dict()).execute()
            st.success("Data Member Diperbarui!"); st.rerun()
    with tab_h:
        st.subheader("Daftar Harga Beli")
        df_p = pd.DataFrame(price_data) if price_data else pd.DataFrame(columns=['item', 'price'])
        ed_p = st.data_editor(df_p, num_rows="dynamic", key="ed_p")
        if st.button("Simpan Harga"):
            for _, row in ed_p.iterrows():
                conn.table("price_data").upsert(row.to_dict()).execute()
                conn.table("stok_gudang").upsert({"item": row['item'], "stok": 0}, on_conflict="item").execute()
            st.success("Harga & Gudang Diperbarui!"); st.rerun()
