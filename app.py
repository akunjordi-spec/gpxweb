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
    st.error(f"❌ Koneksi Secrets Gagal: {e}")
    st.stop()

# --- FUNGSI DATA ---
def load_all_data():
    m = conn.table("members_data").select("*").execute()
    s = conn.table("stok_gudang").select("*").execute()
    b = conn.table("stock_data").select("*").execute()
    p = conn.table("price_data").select("*").execute()
    return m.data, s.data, b.data, p.data

members_data, stok_data, bibit_data, price_data = load_all_data()

# --- NAVIGASI ---
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
        else: st.info("Belum ada data barang di gudang.")
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
        st.table(top_phys.rename(columns={'nama': 'Nama Member', 'total_kembali': 'Total Unit', 'total_uang': 'Saldo Rp'}))

# --- MENU: SETORAN & BIBIT ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan Member")
    if not members_data:
        st.warning("⚠️ Belum ada member. Silakan tambah member di menu Pengaturan.")
    else:
        m_name = st.selectbox("Pilih Nama Member:", sorted([m['nama'] for m in members_data]))
        tab1, tab2 = st.tabs(["🍀 Setoran Hasil Panen", "🌱 Pengambilan Bibit"])
        
        with tab1:
            if not price_data:
                st.info("💡 Belum ada daftar harga barang. Tambahkan barang di menu Pengaturan agar form muncul.")
            else:
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
                        msg = f"**SETORAN {datetime.now().strftime('%d/%m/%y')}**\n\n**{m_name}**\n" + "\n".join(rincian_msg) + f"\n**TOTAL : {total_rp:,}**"
                        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
                        st.success("Terkirim!")
                    else: st.warning("Isi jumlah barang!")

# --- MENU: ADMIN APPROVAL ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    tasks = conn.table("pending_tasks").select("*").eq("status", "Pending").execute()
    if not tasks.data:
        st.info("Tidak ada laporan baru.")
    else:
        for t in tasks.data:
            with st.expander(f"📌 {t['user_nama']} - {t['tipe']}"):
                st.write(f"Rincian: {t['detail']}")
                if st.button("KONFIRMASI ✅", key=f"app_{t['id']}"):
                    # Logika update stok & saldo (seperti sebelumnya)
                    conn.table("pending_tasks").update({"status": "Approved"}).eq("id", t['id']).execute()
                    st.rerun()

# --- MENU: PENGATURAN (UNTUK EDIT NAMA & HARGA) ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan Harga & Member")
    t1, t2 = st.tabs(["👥 Manajemen Member", "💵 Harga & Jenis Barang"])
    
    with t1:
        st.subheader("Daftar Member")
        st.write("Edit nama atau tambah baris baru di bawah:")
        df_m = pd.DataFrame(members_data) if members_data else pd.DataFrame(columns=['nama', 'total_terima', 'total_kembali', 'total_uang'])
        edited_m = st.data_editor(df_m, num_rows="dynamic", key="editor_member")
        if st.button("Simpan Perubahan Member"):
            for _, row in edited_m.iterrows():
                conn.table("members_data").upsert(row.to_dict()).execute()
            st.success("Member diperbarui!")
            st.rerun()

    with t2:
        st.subheader("Daftar Harga Beli")
        st.write("Masukkan nama barang (CENGKEH, dll) dan harganya:")
        df_p = pd.DataFrame(price_data) if price_data else pd.DataFrame(columns=['item', 'price'])
        edited_p = st.data_editor(df_p, num_rows="dynamic", key="editor_harga")
        if st.button("Simpan Harga & Barang"):
            for _, row in edited_p.iterrows():
                conn.table("price_data").upsert(row.to_dict()).execute()
                conn.table("stok_gudang").upsert({"item": row['item'], "stok": 0}, on_conflict="item").execute()
            st.success("Harga diperbarui!")
            st.rerun()
