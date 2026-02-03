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
    # Memastikan koneksi menggunakan key yang benar dari Secrets
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
    # Perbaikan sintaks query untuk library terbaru
    m = conn.table("members_data").select("*").execute()
    s = conn.table("stok_gudang").select("*").execute()
    b = conn.table("stock_data").select("*").execute()
    p = conn.table("price_data").select("*").execute()
    return m.data, s.data, b.data, p.data

# Inisialisasi Data
try:
    members_data, stok_data, bibit_data, price_data = load_all_data()
except Exception as e:
    st.error(f"❌ Error mengambil data dari tabel: {e}")
    st.info("Pastikan tabel sudah dibuat di SQL Editor Supabase.")
    st.stop()

# --- 4. SIDEBAR ---
st.sidebar.title("🏢 MENU NAVIGASI")
menu = st.sidebar.radio("Pilih Menu:", ["📊 Dashboard", "📝 Setoran & Bibit", "✅ Admin Approval", "💰 Pengaturan"])

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
    df_m = pd.DataFrame(members_data)
    if not df_m.empty:
        top_phys = df_m.nlargest(10, 'total_kembali')[['nama', 'total_kembali', 'total_uang']]
        st.table(top_phys.rename(columns={'nama': 'Nama Member', 'total_kembali': 'Total Unit Disetor', 'total_uang': 'Saldo Rp'}))

# --- MENU: SETORAN & BIBIT ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan Member")
    m_name = st.selectbox("Pilih Nama Member:", sorted([m['nama'] for m in members_data]) if members_data else ["Belum ada member"])
    
    tab1, tab2 = st.tabs(["🍀 Setoran Hasil Panen", "🌱 Pengambilan Bibit"])
    
    with tab1:
        prices = {p['item']: p['price'] for p in price_data}
        input_data, total_rp, rincian_msg = {}, 0, []
        cols = st.columns(3)
        for i, (item, harga) in enumerate(prices.items()):
            qty = cols[i % 3].number_input(f"{item} (Rp{harga:,})", min_value=0, step=1, key=f"setor_{item}")
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
                tgl = datetime.now().strftime("%d/%m/%y")
                msg = f"**SETORAN {tgl}**\n\n**{m_name}**\n" + "\n".join(rincian_msg) + f"\n**TOTAL : {total_rp:,}**"
                send_to_discord(msg)
                st.success("Terkirim! Menunggu konfirmasi.")
            else: st.warning("Isi jumlah barang!")

    with tab2:
        b_item = st.selectbox("Pilih Jenis Bibit:", [b['item'] for b in bibit_data] if bibit_data else ["Kosong"])
        b_qty = st.number_input("Jumlah Ambil:", min_value=1, step=1)
        if st.button("Ajukan Ambil Bibit 🌱"):
            conn.table("pending_tasks").insert({
                "user_nama": m_name, "tipe": "AMBIL", "detail": f"{b_item}:{b_qty}",
                "total_nominal": 0, "status": "Pending"
            }).execute()
            st.success("Permintaan dikirim!")

# --- MENU: ADMIN APPROVAL ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    tasks = conn.table("pending_tasks").select("*").eq("status", "Pending").execute()
    
    if not tasks.data:
        st.info("Tidak ada laporan baru.")
    else:
        for t in tasks.data:
            with st.expander(f"📌 {t['user_nama']} - {t['tipe']} - Rp{t['total_nominal']:,}"):
                st.write(f"Rincian: {t['detail']}")
                if st.button("KONFIRMASI ✅", key=f"app_{t['id']}"):
                    if t['tipe'] == "SETOR":
                        details = ast.literal_eval(t['detail'])
                        # Update Member & Stok
                        m_curr = next(m for m in members_data if m['nama'] == t['user_nama'])
                        conn.table("members_data").update({
                            "total_uang": int(m_curr['total_uang']) + int(t['total_nominal']),
                            "total_kembali": int(m_curr['total_kembali']) + sum(details.values())
                        }).eq("nama", t['user_nama']).execute()
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
                    st.rerun()

# --- MENU: PENGATURAN ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan")
    t1, t2 = st.tabs(["👥 Member", "💵 Harga"])
    with t1:
        df_edit = st.data_editor(pd.DataFrame(members_data), num_rows="dynamic")
        if st.button("Update Member"):
            for _, row in df_edit.iterrows():
                conn.table("members_data").upsert(row.to_dict()).execute()
            st.rerun()
    with t2:
        df_p = st.data_editor(pd.DataFrame(price_data), num_rows="dynamic")
        if st.button("Update Harga"):
            for _, row in df_p.iterrows():
                conn.table("price_data").upsert(row.to_dict()).execute()
                conn.table("stok_gudang").upsert({"item": row['item'], "stok": 0}, on_conflict="item").execute()
            st.rerun()
