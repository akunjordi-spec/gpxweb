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
    st.error("Koneksi gagal! Cek Secrets di Streamlit Cloud.")
    st.stop()

# --- FUNGSI LOAD DATA (DIOPTIMALKAN) ---
def load_all_data():
    try:
        # Mengambil data langsung dari tabel yang sudah kamu isi
        m = conn.table("members_data").select("*").execute()
        s = conn.table("stok_gudang").select("*").execute()
        p = conn.table("price_data").select("*").execute()
        return m.data, s.data, p.data
    except Exception as e:
        # Jika RLS masih aktif, error akan muncul di sini
        st.sidebar.error(f"Gagal memuat data: {e}")
        return [], [], []

# Ambil data dari database
members_data, stok_data, price_data = load_all_data()

# --- SIDEBAR MENU ---
st.sidebar.title("🏢 MENU UTAMA")
menu = st.sidebar.radio("Navigasi:", ["📊 Dashboard", "📝 Setoran & Bibit", "✅ Admin Approval", "💰 Pengaturan"])

# --- MENU: DASHBOARD (LEADERBOARD FISIK) ---
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
        # Menampilkan ranking berdasarkan unit yang dikumpulkan
        top = df_m.nlargest(10, 'total_kembali')[['nama', 'total_kembali', 'total_uang']]
        st.table(top.rename(columns={'nama': 'Nama', 'total_kembali': 'Total Unit', 'total_uang': 'Saldo Rp'}))
    else:
        st.info("Belum ada data member untuk ditampilkan.")

# --- MENU: SETORAN & BIBIT (FORM OTOMATIS DARI DATABASE) ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan Member")
    
    if not members_data or not price_data:
        st.warning("⚠️ Data tidak ditemukan. Pastikan RLS di Supabase sudah dimatikan!")
    else:
        m_name = st.selectbox("Pilih Member:", sorted([m['nama'] for m in members_data]))
        
        # Form dinamis berdasarkan tabel price_data yang kamu isi (AKAR, BUAH, dll)
        st.write("### Masukkan Hasil Panen:")
        input_data, total_rp, rincian_txt = {}, 0, []
        
        # Membuat grid 3 kolom untuk input barang
        cols = st.columns(3)
        for i, row in enumerate(price_data):
            item = row['item']
            harga = row['price']
            qty = cols[i % 3].number_input(f"{item} (Rp{harga:,})", min_value=0, step=1, key=f"in_{item}")
            
            if qty > 0:
                input_data[item] = qty
                total_rp += (qty * harga)
                rincian_txt.append(f"{item}: {qty}")

        if st.button("Kirim Laporan Ke Admin 🚀"):
            if input_data:
                # Masuk ke antrean approval
                conn.table("pending_tasks").insert({
                    "user_nama": m_name, "tipe": "SETOR", "detail": str(input_data),
                    "total_nominal": total_rp, "status": "Pending"
                }).execute()
                
                # Bot Discord Notifikasi Laporan Masuk
                msg = f"📩 **LAPORAN BARU**\nMember: **{m_name}**\nDetail: {', '.join(rincian_txt)}\nTotal: **Rp {total_rp:,}**"
                requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
                st.success("Laporan berhasil dikirim! Menunggu konfirmasi admin.")
            else:
                st.warning("Silakan isi jumlah barang terlebih dahulu.")

# --- MENU: ADMIN APPROVAL ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    try:
        tasks = conn.table("pending_tasks").select("*").eq("status", "Pending").execute()
        if not tasks.data:
            st.info("✅ Belum ada antrean laporan baru.")
        else:
            for t in tasks.data:
                with st.expander(f"📌 {t['user_nama']} - Rp{t['total_nominal']:,}"):
                    st.write(f"Rincian: {t['detail']}")
                    if st.button("SETUJUI & KONFIRMASI BOT ✅", key=f"btn_{t['id']}"):
                        details = ast.literal_eval(t['detail'])
                        m_curr = next(m for m in members_data if m['nama'] == t['user_nama'])
                        
                        # Update Saldo Member & Leaderboard
                        conn.table("members_data").update({
                            "total_uang": int(m_curr.get('total_uang', 0)) + int(t['total_nominal']),
                            "total_kembali": int(m_curr.get('total_kembali', 0)) + sum(details.values())
                        }).eq("nama", t['user_nama']).execute()
                        
                        # Update Stok Gudang
                        for it, q in details.items():
                            s_curr = next((s for s in stok_data if s['item'] == it), None)
                            if s_curr:
                                conn.table("stok_gudang").update({"stok": int(s_curr['stok']) + q}).eq("item", it).execute()
                        
                        # Tandai Task Selesai
                        conn.table("pending_tasks").update({"status": "Approved"}).eq("id", t['id']).execute()
                        
                        # Bot Discord Notifikasi Approval
                        msg_app = f"✅ **PEMBAYARAN DISETUJUI**\nMember: **{t['user_nama']}**\nSaldo Masuk: **Rp {t['total_nominal']:,}**\n*Status: Saldo & Stok Terupdate*"
                        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg_app})
                        
                        st.success("Berhasil di-approve!")
                        st.rerun()
    except Exception as e:
        st.error(f"Gagal memuat antrean: {e}")

# --- MENU: PENGATURAN ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan Database")
    t1, t2 = st.tabs(["👥 Edit Nama Member", "💵 Edit Harga & Barang"])
    
    with t1:
        df_m = pd.DataFrame(members_data) if members_data else pd.DataFrame(columns=['nama', 'total_uang', 'total_kembali'])
        ed_m = st.data_editor(df_m, num_rows="dynamic", key="ed_m")
        if st.button("Simpan Member"):
            for _, row in ed_m.iterrows():
                conn.table("members_data").upsert(row.to_dict(), on_conflict="nama").execute()
            st.rerun()
            
    with t2:
        df_p = pd.DataFrame(price_data) if price_data else pd.DataFrame(columns=['item', 'price'])
        ed_p = st.data_editor(df_p, num_rows="dynamic", key="ed_p")
        if st.button("Simpan Harga"):
            for _, row in ed_p.iterrows():
                d = row.to_dict()
                conn.table("price_data").upsert(d, on_conflict="item").execute()
                conn.table("stok_gudang").upsert({"item": d['item'], "stok": 0}, on_conflict="item").execute()
            st.rerun()
