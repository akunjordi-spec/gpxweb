import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import requests
import ast

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="GPX Game Office", layout="wide", page_icon="🏢")

# --- 2. KONEKSI DATABASE ---
try:
    # Koneksi menggunakan URL & Key langsung dari secrets untuk hindari error 'Not Provided'
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

# --- 3. FUNGSI HELPER ---
def send_to_discord(message):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
    except:
        pass

def load_all_data():
    m = conn.query("*", table="members_data").execute()
    s = conn.query("*", table="stok_gudang").execute()
    b = conn.query("*", table="stock_data").execute()
    p = conn.query("*", table="price_data").execute()
    return m.data, s.data, b.data, p.data

# Inisialisasi Data
members_data, stok_data, bibit_data, price_data = load_all_data()

# --- 4. SIDEBAR ---
st.sidebar.title("🏢 MENU NAVIGASI")
menu = st.sidebar.radio("Pilih Menu:", ["📊 Dashboard", "📝 Setoran & Bibit", "✅ Admin Approval", "💰 Pengaturan"])

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring Dashboard GPX")
    
    # Baris Atas: Stok
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

    # Leaderboard Berdasarkan Unit Fisik (Penyetor Terajin)
    st.subheader("🏆 Leaderboard Penyetor Terajin (Unit Fisik)")
    df_m = pd.DataFrame(members_data)
    if not df_m.empty:
        # Sort berdasarkan total_kembali
        top_phys = df_m.nlargest(10, 'total_kembali')[['nama', 'total_kembali', 'total_uang']]
        st.table(top_phys.rename(columns={'nama': 'Nama Member', 'total_kembali': 'Total Unit Disetor', 'total_uang': 'Saldo Rp'}))

# --- MENU: SETORAN & BIBIT ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan Member")
    m_name = st.selectbox("Pilih Nama Member:", sorted([m['nama'] for m in members_data]))
    
    tab1, tab2 = st.tabs(["🍀 Setoran Hasil Panen", "🌱 Pengambilan Bibit"])
    
    with tab1:
        st.write("Masukkan jumlah barang yang disetor:")
        prices = {p['item']: p['price'] for p in price_data}
        input_data = {}
        total_rp = 0
        rincian_msg = []
        
        cols = st.columns(3)
        for i, (item, harga) in enumerate(prices.items()):
            qty = cols[i % 3].number_input(f"{item} (Rp{harga:,})", min_value=0, step=1)
            if qty > 0:
                input_data[item] = qty
                total_rp += (qty * harga)
                rincian_msg.append(f"{item} : {qty:,}")
        
        if st.button("Kirim Laporan Setoran 🚀"):
            if input_data:
                conn.table("pending_tasks").insert({
                    "user_nama": m_name, "tipe": "SETOR", "detail": str(input_data),
                    "total_nominal": total_rp, "status": "Pending"
                }).execute()
                
                # Format Discord Sesuai Request
                tgl = datetime.now().strftime("%d/%m/%y")
                msg = f"**SETORAN {tgl}**\n\n**{m_name}**\n" + "\n".join(rincian_msg) + f"\n**TOTAL : {total_rp:,}**"
                send_to_discord(msg)
                st.success("Laporan terkirim! Menunggu Approval Admin.")
            else:
                st.warning("Isi jumlah barang dulu!")

    with tab2:
        b_item = st.selectbox("Pilih Jenis Bibit:", [b['item'] for b in bibit_data])
        b_qty = st.number_input("Jumlah Ambil:", min_value=1, step=1)
        if st.button("Ajukan Ambil Bibit 🌱"):
            conn.table("pending_tasks").insert({
                "user_nama": m_name, "tipe": "AMBIL", "detail": f"{b_item}:{b_qty}",
                "total_nominal": 0, "status": "Pending"
            }).execute()
            st.success("Permintaan bibit dikirim!")

# --- MENU: ADMIN APPROVAL ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    tasks = conn.query("*", table="pending_tasks").eq("status", "Pending").execute()
    
    if not tasks.data:
        st.info("Semua laporan sudah diproses.")
    else:
        for t in tasks.data:
            with st.expander(f"📌 {t['user_nama']} - {t['tipe']} - Rp{t['total_nominal']:,}"):
                st.write(f"Rincian: {t['detail']}")
                if st.button("SETUJUI & UPDATE DATA", key=f"app_{t['id']}"):
                    if t['tipe'] == "SETOR":
                        details = ast.literal_eval(t['detail'])
                        total_unit = sum(details.values())
                        # Update Member (Saldo & Leaderboard Fisik)
                        m_curr = next(m for m in members_data if m['nama'] == t['user_nama'])
                        conn.table("members_data").update({
                            "total_uang": int(m_curr['total_uang']) + int(t['total_nominal']),
                            "total_kembali": int(m_curr['total_kembali']) + total_unit
                        }).eq("nama", t['user_nama']).execute()
                        # Update Stok Gudang
                        for it, q in details.items():
                            s_curr = next(s for s in stok_data if s['item'] == it)
                            conn.table("stok_gudang").update({"stok": int(s_curr['stok']) + q}).eq("item", it).execute()
                        send_to_discord(f"✅ **DIBAYAR:** {t['user_nama']} senilai Rp {t['total_nominal']:,}")

                    elif t['tipe'] == "AMBIL":
                        it_b, q_b = t['detail'].split(":")
                        m_curr = next(m for m in members_data if m['nama'] == t['user_nama'])
                        conn.table("members_data").update({"total_terima": int(m_curr['total_terima']) + int(q_b)}).eq("nama", t['user_nama']).execute()
                        b_curr = next(b for b in bibit_data if b['item'] == it_b)
                        conn.table("stock_data").update({"qty": int(b_curr['qty']) - int(q_b)}).eq("item", it_b).execute()

                    conn.table("pending_tasks").update({"status": "Approved"}).eq("id", t['id']).execute()
                    st.success("Data berhasil diupdate!"); st.rerun()

# --- MENU: PENGATURAN ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan Database")
    t1, t2 = st.tabs(["👥 Member", "💵 Harga & Barang"])
    
    with t1:
        st.subheader("Manajemen Member")
        df_edit = st.data_editor(pd.DataFrame(members_data), num_rows="dynamic")
        if st.button("Simpan Data Member"):
            for _, row in df_edit.iterrows():
                conn.table("members_data").upsert(row.to_dict()).execute()
            st.success("Member diperbarui!"); st.rerun()
            
    with t2:
        st.subheader("Harga Beli Barang")
        df_p = st.data_editor(pd.DataFrame(price_data), num_rows="dynamic")
        if st.button("Simpan Harga"):
            for _, row in df_p.iterrows():
                conn.table("price_data").upsert(row.to_dict()).execute()
                # Pastikan barang ada di stok_gudang
                conn.table("stok_gudang").upsert({"item": row['item'], "stok": 0}, on_conflict="item").execute()
            st.success("Harga & Gudang diperbarui!"); st.rerun()
