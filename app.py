import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import requests
import ast

st.set_page_config(page_title="GPX Game Office", layout="wide", page_icon="🏢")

# --- KONEKSI ---
try:
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["SUPABASE_URL"],
        key=st.secrets["SUPABASE_KEY"]
    )
    DISCORD_WEBHOOK_URL = st.secrets["MY_WEBHOOK_URL"]
except Exception as e:
    st.error(f"Gagal koneksi! Pastikan Secrets sudah benar.")
    st.stop()

# --- FUNGSI LOAD DATA ---
def load_all_data():
    try:
        m = conn.table("members_data").select("*").execute()
        s = conn.table("stok_gudang").select("*").execute()
        p = conn.table("price_data").select("*").execute()
        return m.data, s.data, p.data
    except Exception:
        return [], [], []

members_data, stok_data, price_data = load_all_data()

# --- SIDEBAR ---
st.sidebar.title("🏢 MENU UTAMA")
menu = st.sidebar.radio("Navigasi:", ["📊 Dashboard", "📝 Setoran & Bibit", "✅ Admin Approval", "💰 Pengaturan"])

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring Dashboard GPX")
    if stok_data:
        st.subheader("📦 Stok Gudang Pusat")
        cols = st.columns(len(stok_data))
        for i, item in enumerate(stok_data):
            cols[i].metric(item['item'], f"{item['stok']:,} Unit")
    
    st.divider()
    st.subheader("🏆 Leaderboard Penyetor Terajin")
    if members_data:
        df_m = pd.DataFrame(members_data)
        # Menghitung berdasarkan unit fisik
        top = df_m.nlargest(10, 'total_kembali')[['nama', 'total_kembali', 'total_uang']]
        st.table(top.rename(columns={'nama': 'Nama', 'total_kembali': 'Total Unit', 'total_uang': 'Saldo Rp'}))

# --- MENU: SETORAN & BIBIT ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan Member")
    if not members_data or not price_data:
        st.warning("⚠️ Atur Member dan Harga di menu Pengaturan terlebih dahulu!")
    else:
        m_name = st.selectbox("Pilih Member:", sorted([m['nama'] for m in members_data]))
        prices = {p['item']: p['price'] for p in price_data}
        
        input_data, total_rp, rincian_txt = {}, 0, []
        st.write("### Masukkan Hasil Panen:")
        cols = st.columns(3)
        for i, (item, harga) in enumerate(prices.items()):
            qty = cols[i % 3].number_input(f"{item} (Rp{harga:,})", min_value=0, step=1, key=f"in_{item}")
            if qty > 0:
                input_data[item] = qty
                total_rp += (qty * harga)
                rincian_txt.append(f"{item}: {qty}")

        if st.button("Kirim Laporan Ke Admin 🚀"):
            if input_data:
                conn.table("pending_tasks").insert({
                    "user_nama": m_name, "tipe": "SETOR", "detail": str(input_data),
                    "total_nominal": total_rp, "status": "Pending"
                }).execute()
                # Notifikasi Discord
                msg = f"**SETORAN BARU**\nMember: {m_name}\n" + "\n".join(rincian_txt) + f"\nTotal: Rp {total_rp:,}"
                requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
                st.success("Laporan terkirim!")
            else: st.warning("Isi jumlah barang!")

# --- MENU: ADMIN APPROVAL ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    try:
        tasks = conn.table("pending_tasks").select("*").eq("status", "Pending").execute()
        if not tasks.data:
            st.info("Belum ada antrean setoran.")
        else:
            for t in tasks.data:
                with st.expander(f"📌 {t['user_nama']} - Rp{t['total_nominal']:,}"):
                    st.write(f"Rincian: {t['detail']}")
                    if st.button("SETUJUI ✅", key=f"btn_{t['id']}"):
                        details = ast.literal_eval(t['detail'])
                        m_curr = next(m for m in members_data if m['nama'] == t['user_nama'])
                        
                        # 1. Update Member
                        conn.table("members_data").update({
                            "total_uang": int(m_curr.get('total_uang', 0)) + int(t['total_nominal']),
                            "total_kembali": int(m_curr.get('total_kembali', 0)) + sum(details.values())
                        }).eq("nama", t['user_nama']).execute()
                        
                        # 2. Update Stok
                        for it, q in details.items():
                            s_curr = next((s for s in stok_data if s['item'] == it), None)
                            if s_curr:
                                conn.table("stok_gudang").update({"stok": int(s_curr['stok']) + q}).eq("item", it).execute()
                        
                        # 3. Tandai Selesai
                        conn.table("pending_tasks").update({"status": "Approved"}).eq("id", t['id']).execute()
                        st.rerun()
    except Exception as e:
        st.error(f"Gagal memuat antrean: {e}")

# --- MENU: PENGATURAN ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan Database")
    t1, t2 = st.tabs(["👥 Edit Nama Member", "💵 Edit Harga & Barang"])
    
    with t1:
        df_m = pd.DataFrame(members_data) if members_data else pd.DataFrame(columns=['nama', 'total_uang', 'total_kembali'])
        # Pastikan kolom nama ada dan tidak diedit sembarangan karena itu Primary Key kita
        ed_m = st.data_editor(df_m, num_rows="dynamic", key="editor_m")
        if st.button("Simpan Member"):
            for _, row in ed_m.iterrows():
                data = row.to_dict()
                # Bersihkan data None agar tidak error di database
                data = {k: (v if v is not None else 0) for k, v in data.items()}
                conn.table("members_data").upsert(data, on_conflict="nama").execute()
            st.success("Data Member Berhasil Disimpan!")
            st.rerun()

    with t2:
        df_p = pd.DataFrame(price_data) if price_data else pd.DataFrame(columns=['item', 'price'])
        ed_p = st.data_editor(df_p, num_rows="dynamic", key="editor_p")
        if st.button("Simpan Harga"):
            for _, row in ed_p.iterrows():
                data_p = row.to_dict()
                conn.table("price_data").upsert(data_p, on_conflict="item").execute()
                # Otomatis buat rumah di stok_gudang jika barang baru
                conn.table("stok_gudang").upsert({"item": data_p['item'], "stok": 0}, on_conflict="item").execute()
            st.success("Harga dan Stok Gudang Berhasil Disimpan!")
            st.rerun()
