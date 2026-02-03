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
    st.error("Koneksi gagal! Cek Secrets di Streamlit Cloud."); st.stop()

# Fungsi Ambil Data Fresh
def get_data(table):
    try:
        res = conn.table(table).select("*").execute()
        return res.data if res.data else []
    except: return []

# Load Semua Data
members = get_data("members_data")
prices = get_data("price_data")
stok_gdg = get_data("stok_gudang")
bibit_gdg = get_data("stock_data")

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("🏢 GPX MANAGEMENT")
menu = st.sidebar.radio("MENU:", ["📊 Dashboard", "📝 Setoran & Bibit", "✅ Admin Approval", "💰 Pengaturan"])

# --- 1. DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring Dashboard")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📦 Stok Hasil Panen")
        if stok_gdg:
            for i in stok_gdg: st.info(f"**{i['item']}**: {i.get('stok', 0):,} Unit")
    with col2:
        st.subheader("🌱 Stok Bibit Gudang")
        if bibit_gdg:
            for i in bibit_gdg: st.success(f"**{i['item']}**: {i.get('qty', 0):,} Pcs")
    
    st.divider()
    st.subheader("🏆 Status & Leaderboard Member")
    if members:
        df_m = pd.DataFrame(members)
        for c in ['total_terima', 'total_kembali', 'total_uang']:
            if c not in df_m.columns: df_m[c] = 0
        st.table(df_m[['nama', 'total_terima', 'total_kembali', 'total_uang']].rename(
            columns={'nama': 'Member', 'total_terima': 'Bibit di Tangan', 
                     'total_kembali': 'Total Setoran', 'total_uang': 'Saldo (Rp)'}
        ))

# --- 2. SETORAN & BIBIT ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan Member")
    if not members:
        st.warning("Tambahkan member di menu Pengaturan!")
    else:
        m_name = st.selectbox("Pilih Member:", [m['nama'] for m in members])
        tab1, tab2 = st.tabs(["🍀 Setoran Panen", "🌱 Kelola Bibit"])
        
        with tab1:
            if not prices:
                st.info("Atur harga barang di menu Pengaturan.")
            else:
                input_setor, total_rp, rincian_discord_list = {}, 0, []
                cols = st.columns(3)
                for idx, p in enumerate(prices):
                    q = cols[idx % 3].number_input(f"{p['item']}", min_value=0, step=1, key=f"s_{p['item']}")
                    if q > 0:
                        input_setor[p['item']] = q
                        total_rp += (q * p['price'])
                        rincian_discord_list.append(f"{p['item'].upper()} : {q}")
                
                if st.button("Kirim Laporan Setoran 🚀"):
                    if input_setor:
                        tgl_skrg = datetime.now().strftime("%d/%m/%y")
                        rincian_txt = "\n".join(rincian_discord_list)
                        
                        # FORMAT DISCORD SESUAI PERMINTAAN
                        pesan_setoran = (
                            f"**SETORAN {tgl_skrg}**\n\n"
                            f"**{m_name.upper()}**\n"
                            f"{rincian_txt}\n"
                            f"**TOTAL : {total_rp:,}**"
                        )
                        
                        conn.table("pending_tasks").insert({
                            "user_nama": m_name, "tipe": "SETOR", 
                            "detail": str(input_setor), "total_nominal": total_rp, "status": "Pending"
                        }).execute()
                        
                        requests.post(DISCORD_WEBHOOK_URL, json={"content": pesan_setoran})
                        st.success("Setoran terkirim ke Discord!")

        with tab2:
            st.subheader("Ambil atau Kembalikan Bibit")
            aksi = st.radio("Aksi:", ["Ambil dari Gudang", "Kembalikan ke Gudang (Retur)"])
            if not bibit_gdg:
                st.info("Data bibit kosong.")
            else:
                b_pilih = st.selectbox("Pilih Jenis Bibit:", [b['item'] for b in bibit_gdg])
                b_qty = st.number_input("Jumlah Pcs:", min_value=0, step=1)
                
                if st.button("Kirim Laporan Bibit 🚀"):
                    if b_qty > 0:
                        tipe_b = "AMBIL_BIBIT" if aksi == "Ambil dari Gudang" else "RETUR_BIBIT"
                        conn.table("pending_tasks").insert({
                            "user_nama": m_name, "tipe": tipe_b, 
                            "detail": str({b_pilih: b_qty}), "total_nominal": 0, "status": "Pending"
                        }).execute()
                        
                        icon = "🌱" if tipe_b == "AMBIL_BIBIT" else "🔄"
                        msg_b = f"{icon} **LAPORAN BIBIT**\n👤 Member: **{m_name.upper()}**\n📝 Aksi: {aksi}\n📦 Detail: {b_pilih} ({b_qty} Pcs)"
                        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg_b})
                        st.success("Laporan Bibit Terkirim!")

# --- 3. ADMIN APPROVAL ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    tasks = conn.table("pending_tasks").select("*").eq("status", "Pending").execute().data
    if not tasks:
        st.info("Antrean kosong.")
    else:
        for t in tasks:
            with st.expander(f"📌 {t['user_nama']} - {t['tipe']}"):
                st.write(f"Rincian: {t['detail']}")
                if st.button("SETUJUI & BAYAR ✅", key=f"app_{t['id']}"):
                    det = ast.literal_eval(t['detail'])
                    m_curr = next((m for m in members if m['nama'] == t['user_nama']), None)
                    
                    if m_curr:
                        if t['tipe'] == "SETOR":
                            # Update Saldo & Unit
                            conn.table("members_data").update({
                                "total_uang": m_curr['total_uang'] + t['total_nominal'],
                                "total_kembali": m_curr['total_kembali'] + sum(det.values())
                            }).eq("nama", t['user_nama']).execute()
                            # Update Stok Gudang Panen
                            for it, q in det.items():
                                s_curr = next((s for s in stok_gdg if s['item'] == it), None)
                                if s_curr: conn.table("stok_gudang").update({"stok": s_curr['stok'] + q}).eq("item", it).execute()
                            
                            requests.post(DISCORD_WEBHOOK_URL, json={"content": f"✅ **PEMBAYARAN LUNAS**: {t['user_nama'].upper()} senilai Rp {t['total_nominal']:,} telah dikonfirmasi."})

                        elif t['tipe'] == "AMBIL_BIBIT":
                            for it, q in det.items():
                                b_curr = next((b for b in bibit_gdg if b['item'] == it), None)
                                if b_curr:
                                    conn.table("stock_data").update({"qty": b_curr['qty'] - q}).eq("item", it).execute()
                                    conn.table("members_data").update({"total_terima": m_curr['total_terima'] + q}).eq("nama", t['user_nama']).execute()

                        elif t['tipe'] == "RETUR_BIBIT":
                            for it, q in det.items():
                                b_curr = next((b for b in bibit_gdg if b['item'] == it), None)
                                if b_curr:
                                    # LOGIKA JOE: Stok Gudang nambah, Bibit Member kurang
                                    conn.table("stock_data").update({"qty": b_curr['qty'] + q}).eq("item", it).execute()
                                    conn.table("members_data").update({"total_terima": m_curr['total_terima'] - q}).eq("nama", t['user_nama']).execute()
                    
                    conn.table("pending_tasks").update({"status": "Approved"}).eq("id", t['id']).execute()
                    st.rerun()

# --- 4. PENGATURAN ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan Database")
    t1, t2, t3 = st.tabs(["👤 Member", "💰 Harga", "🌱 Bibit"])
    
    with t1:
        df_m = pd.DataFrame(members) if members else pd.DataFrame(columns=['nama', 'total_uang', 'total_kembali', 'total_terima'])
        ed_m = st.data_editor(df_m, num_rows="dynamic", key="ed_m")
        if st.button("Simpan Member"):
            for _, r in ed_m.iterrows(): conn.table("members_data").upsert(r.to_dict()).execute()
            st.rerun()
            
    with t2:
        df_p = pd.DataFrame(prices) if prices else pd.DataFrame(columns=['item', 'price'])
        ed_p = st.data_editor(df_p, num_rows="dynamic", key="ed_p")
        if st.button("Simpan Harga"):
            for _, r in ed_p.iterrows():
                conn.table("price_data").upsert(r.to_dict()).execute()
                conn.table("stok_gudang").upsert({"item": r['item'], "stok": 0}).execute()
            st.rerun()

    with t3:
        df_b = pd.DataFrame(bibit_gdg) if bibit_gdg else pd.DataFrame(columns=['item', 'qty'])
        ed_b = st.data_editor(df_b, num_rows="dynamic", key="ed_b")
        if st.button("Simpan Bibit"):
            for _, r in ed_b.iterrows(): conn.table("stock_data").upsert(r.to_dict()).execute()
            st.rerun()
