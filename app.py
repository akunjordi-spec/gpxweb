import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import requests
import ast

st.set_page_config(page_title="GPX Game Office", layout="wide")

# --- KONEKSI ---
try:
    # Menggunakan koneksi resmi st_supabase_connection
    conn = st.connection("supabase", type=SupabaseConnection, 
                         url=st.secrets["SUPABASE_URL"], 
                         key=st.secrets["SUPABASE_KEY"])
    DISCORD_WEBHOOK_URL = st.secrets["MY_WEBHOOK_URL"]
except:
    st.error("Koneksi gagal! Pastikan secrets SUPABASE_URL dan SUPABASE_KEY sudah benar.")
    st.stop()

# Fungsi Ambil Data (Menggunakan sintaks terbaru .table().select())
def get_all_data():
    try:
        m = conn.table("members_data").select("*").execute()
        p = conn.table("price_data").select("*").execute()
        s = conn.table("stok_gudang").select("*").execute()
        b = conn.table("stock_data").select("*").execute()
        return m.data, p.data, s.data, b.data
    except Exception as e:
        st.error(f"Error Database: {e}")
        return [], [], [], []

# Refresh data setiap load page
members, prices, stok_gdg, bibit_gdg = get_all_data()

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("🏢 MENU UTAMA")
menu = st.sidebar.radio("Navigasi:", ["📊 Dashboard", "📝 Setoran & Bibit", "✅ Admin Approval", "💰 Pengaturan"])

# --- 1. DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring Dashboard GPX")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📦 Stok Gudang Panen")
        if stok_gdg:
            for i in stok_gdg: st.info(f"**{i['item']}**: {i.get('stok', 0):,} Unit")
    with col2:
        st.subheader("🌱 Stok Bibit Tersedia")
        if bibit_gdg:
            for i in bibit_gdg: st.success(f"**{i['item']}**: {i.get('qty', 0):,} Pcs")
    
    st.divider()
    st.subheader("🏆 Leaderboard & Status Member")
    if members:
        df_m = pd.DataFrame(members)
        # Pastikan kolom ada agar tidak error
        for col in ['total_terima', 'total_kembali', 'total_uang']:
            if col not in df_m.columns: df_m[col] = 0
            
        st.table(df_m[['nama', 'total_terima', 'total_kembali', 'total_uang']].rename(
            columns={'nama': 'Member', 'total_terima': 'Bibit di Tangan', 
                     'total_kembali': 'Total Setor', 'total_uang': 'Saldo (Rp)'}
        ))

# --- 2. SETORAN & BIBIT ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan Member")
    if not members:
        st.warning("Tambahkan Member di menu Pengaturan!")
    else:
        m_name = st.selectbox("Pilih Nama Member:", [m['nama'] for m in members])
        tab1, tab2 = st.tabs(["🍀 Setoran Hasil Panen", "🌱 Pengambilan Bibit"])
        
        with tab1:
            st.write("### Masukkan Jumlah Barang:")
            if not prices:
                st.info("Daftar harga kosong. Atur di Pengaturan.")
            else:
                input_setor, total_rp, rincian = {}, 0, []
                # Grid 3 kolom agar rapi
                cols = st.columns(3)
                for idx, p in enumerate(prices):
                    qty = cols[idx % 3].number_input(f"{p['item']} (Rp{p['price']})", min_value=0, step=1, key=f"in_{p['item']}")
                    if qty > 0:
                        input_setor[p['item']] = qty
                        total_rp += (qty * p['price'])
                        rincian.append(f"{p['item']}: {qty}")
                
                if st.button("Kirim Laporan Setoran 🚀"):
                    if input_setor:
                        conn.table("pending_tasks").insert({
                            "user_nama": m_name, "tipe": "SETOR", "detail": str(input_setor),
                            "total_nominal": total_rp, "status": "Pending"
                        }).execute()
                        requests.post(DISCORD_WEBHOOK_URL, json={"content": f"📩 **SETORAN BARU**: {m_name} | {rincian} | Total: Rp {total_rp:,}"})
                        st.success("Berhasil dikirim!")
                    else: st.warning("Isi jumlah barang dulu!")

        with tab2:
            st.write("### Kelola Stok Bibit:")
            opsi = st.radio("Pilih Aksi:", ["Ambil Bibit Baru", "Kembalikan Bibit (Retur)"])
            if not bibit_gdg:
                st.info("Data bibit tidak ada.")
            else:
                b_pilih = st.selectbox("Jenis Bibit:", [b['item'] for b in bibit_gdg])
                b_qty = st.number_input("Jumlah Pcs:", min_value=0, step=1)
                
                if st.button("Kirim Laporan Bibit 🚀"):
                    if b_qty > 0:
                        tipe_t = "AMBIL_BIBIT" if opsi == "Ambil Bibit Baru" else "RETUR_BIBIT"
                        conn.table("pending_tasks").insert({
                            "user_nama": m_name, "tipe": tipe_t, "detail": str({b_pilih: b_qty}),
                            "total_nominal": 0, "status": "Pending"
                        }).execute()
                        requests.post(DISCORD_WEBHOOK_URL, json={"content": f"🌱 **{tipe_t}**: {m_name} | {b_pilih}: {b_qty} Pcs"})
                        st.success("Laporan Bibit Terkirim!")

# --- 3. ADMIN APPROVAL (BALIK KE PEMBAYARAN) ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    tasks = conn.table("pending_tasks").select("*").eq("status", "Pending").execute().data
    
    if not tasks:
        st.info("Antrean laporan kosong.")
    else:
        for t in tasks:
            with st.expander(f"📌 {t['user_nama']} - {t['tipe']}"):
                st.write(f"Detail: {t['detail']}")
                if t['total_nominal'] > 0:
                    st.success(f"**Total Pembayaran: Rp {t['total_nominal']:,}**")
                
                if st.button("SETUJUI & BAYAR ✅", key=f"app_{t['id']}"):
                    det = ast.literal_eval(t['detail'])
                    m_curr = next((m for m in members if m['nama'] == t['user_nama']), None)
                    
                    if m_curr:
                        if t['tipe'] == "SETOR":
                            # 1. Update Saldo & Setoran Member
                            conn.table("members_data").update({
                                "total_uang": int(m_curr.get('total_uang', 0)) + t['total_nominal'],
                                "total_kembali": int(m_curr.get('total_kembali', 0)) + sum(det.values())
                            }).eq("nama", t['user_nama']).execute()
                            # 2. Update Stok Gudang
                            for it, q in det.items():
                                s_curr = next((s for s in stok_gdg if s['item'] == it), None)
                                if s_curr: conn.table("stok_gudang").update({"stok": s_curr['stok'] + q}).eq("item", it).execute()
                        
                        elif t['tipe'] == "AMBIL_BIBIT":
                            for it, q in det.items():
                                b_curr = next((b for b in bibit_gdg if b['item'] == it), None)
                                if b_curr:
                                    conn.table("stock_data").update({"qty": b_curr['qty'] - q}).eq("item", it).execute()
                                    conn.table("members_data").update({"total_terima": int(m_curr.get('total_terima', 0)) + q}).eq("nama", t['user_nama']).execute()
                        
                        elif t['tipe'] == "RETUR_BIBIT":
                            for it, q in det.items():
                                b_curr = next((b for b in bibit_gdg if b['item'] == it), None)
                                if b_curr:
                                    # LOGIKA JOE: Stok gudang nambah lagi, bibit di tangan member berkurang
                                    conn.table("stock_data").update({"qty": b_curr['qty'] + q}).eq("item", it).execute()
                                    conn.table("members_data").update({"total_terima": int(m_curr.get('total_terima', 0)) - q}).eq("nama", t['user_nama']).execute()

                    # Tandai Task Selesai
                    conn.table("pending_tasks").update({"status": "Approved"}).eq("id", t['id']).execute()
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": f"✅ **TERBAYAR**: Laporan {t['user_nama']} ({t['tipe']}) telah diproses!"})
                    st.rerun()

# --- 4. PENGATURAN ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan Database")
    t1, t2, t3 = st.tabs(["👤 Member", "💰 Harga Panen", "🌱 Jenis Bibit"])
    
    with t1:
        df_m = pd.DataFrame(members) if members else pd.DataFrame(columns=['nama', 'total_uang', 'total_kembali', 'total_terima'])
        ed_m = st.data_editor(df_m, num_rows="dynamic", key="editor_m")
        if st.button("Simpan Member"):
            for _, r in ed_m.iterrows(): conn.table("members_data").upsert(r.to_dict()).execute()
            st.rerun()
            
    with t2:
        df_p = pd.DataFrame(prices) if prices else pd.DataFrame(columns=['item', 'price'])
        ed_p = st.data_editor(df_p, num_rows="dynamic", key="editor_p")
        if st.button("Simpan Harga"):
            for _, r in ed_p.iterrows():
                conn.table("price_data").upsert(r.to_dict()).execute()
                conn.table("stok_gudang").upsert({"item": r['item'], "stok": 0}).execute()
            st.rerun()

    with t3:
        df_b = pd.DataFrame(bibit_gdg) if bibit_gdg else pd.DataFrame(columns=['item', 'qty'])
        ed_b = st.data_editor(df_b, num_rows="dynamic", key="editor_b")
        if st.button("Simpan Bibit"):
            for _, r in ed_b.iterrows(): conn.table("stock_data").upsert(r.to_dict()).execute()
            st.rerun()
