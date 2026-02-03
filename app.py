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

# Fungsi Load Data tanpa Cache untuk Pengaturan (agar tidak blank)
def load_data_fresh(table_name):
    try:
        return conn.table(table_name).select("*").execute().data
    except: return []

# Ambil Data Terbaru
members = load_data_fresh("members_data")
prices = load_data_fresh("price_data")
stok_gdg = load_data_fresh("stok_gudang")
bibit_gdg = load_data_fresh("stock_data")

menu = st.sidebar.radio("Menu:", ["📊 Dashboard", "📝 Setoran & Bibit", "✅ Admin Approval", "💰 Pengaturan"])

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring GPX")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📦 Stok Hasil Panen")
        if stok_gdg:
            for i in stok_gdg: st.write(f"- **{i['item']}**: {i.get('stok', 0):,} Unit")
    with c2:
        st.subheader("🌱 Stok Bibit Gudang")
        if bibit_gdg:
            for i in bibit_gdg: st.write(f"- **{i['item']}**: {i.get('qty', 0):,} Pcs")
    
    st.divider()
    st.subheader("🏆 Status Member")
    if members:
        df_m = pd.DataFrame(members)
        st.table(df_m[['nama', 'total_terima', 'total_kembali', 'total_uang']].rename(
            columns={'total_terima': 'Bibit di Tangan', 'total_kembali': 'Total Setoran (Unit)', 'total_uang': 'Saldo Rp'}
        ))

# --- MENU: SETORAN & BIBIT ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan")
    if not members:
        st.warning("Tambahkan member di menu Pengaturan terlebih dahulu.")
    else:
        m_name = st.selectbox("Pilih Member:", [m['nama'] for m in members])
        t1, t2 = st.tabs(["🍀 Setor Panen", "🌱 Kelola Bibit"])
        
        with t1:
            if not prices:
                st.info("Daftar harga kosong. Isi di menu Pengaturan.")
            else:
                input_setor, total_rp, rincian = {}, 0, []
                for p in prices:
                    q = st.number_input(f"{p['item']} (Rp{p['price']:,})", min_value=0, step=1, key=f"s_{p['item']}")
                    if q > 0:
                        input_setor[p['item']] = q
                        total_rp += (q * p['price'])
                        rincian.append(f"{p['item']}: {q}")
                
                if st.button("Kirim Setoran 🚀"):
                    if input_setor:
                        conn.table("pending_tasks").insert({"user_nama": m_name, "tipe": "SETOR", "detail": str(input_setor), "total_nominal": total_rp}).execute()
                        requests.post(DISCORD_WEBHOOK_URL, json={"content": f"📩 **SETORAN**: {m_name} | {rincian} | Total: Rp {total_rp:,}"})
                        st.success("Setoran terkirim!")

        with t2:
            st.subheader("Ambil atau Kembalikan Bibit")
            opsi = st.radio("Aksi:", ["Ambil dari Gudang", "Kembalikan ke Gudang"])
            if not bibit_gdg:
                st.info("Data bibit kosong. Isi di menu Pengaturan.")
            else:
                b_pilih = st.selectbox("Jenis Bibit:", [b['item'] for b in bibit_gdg])
                b_qty = st.number_input("Jumlah Pcs:", min_value=0, step=1)
                
                if st.button("Kirim Laporan Bibit 🚀"):
                    tipe_task = "AMBIL_BIBIT" if opsi == "Ambil dari Gudang" else "RETUR_BIBIT"
                    conn.table("pending_tasks").insert({"user_nama": m_name, "tipe": tipe_task, "detail": str({b_pilih: b_qty}), "total_nominal": 0}).execute()
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": f"🌱 **{tipe_task}**: {m_name} | {b_pilih}: {b_qty} Pcs"})
                    st.success(f"Laporan {opsi} Berhasil!")

# --- MENU: APPROVAL (Logika Retur Joe) ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    tasks = conn.table("pending_tasks").select("*").eq("status", "Pending").execute().data
    if not tasks:
        st.info("Tidak ada antrean laporan.")
    else:
        for t in tasks:
            with st.expander(f"📌 {t['user_nama']} - {t['tipe']}"):
                st.write(f"Detail: {t['detail']}")
                if st.button("SETUJUI ✅", key=f"app_{t['id']}"):
                    det = ast.literal_eval(t['detail'])
                    m_data = next((m for m in members if m['nama'] == t['user_nama']), None)
                    
                    if m_data:
                        if t['tipe'] == "SETOR":
                            # Saldo & Unit Bertambah
                            conn.table("members_data").update({
                                "total_uang": m_data['total_uang'] + t['total_nominal'], 
                                "total_kembali": m_data['total_kembali'] + sum(det.values())
                            }).eq("nama", t['user_nama']).execute()
                            # Stok Hasil Panen Bertambah
                            for it, q in det.items():
                                s_data = next((s for s in stok_gdg if s['item'] == it), None)
                                if s_data:
                                    conn.table("stok_gudang").update({"stok": s_data['stok'] + q}).eq("item", it).execute()

                        elif t['tipe'] == "AMBIL_BIBIT":
                            for it, q in det.items():
                                b_data = next((b for b in bibit_gdg if b['item'] == it), None)
                                if b_data:
                                    conn.table("stock_data").update({"qty": b_data['qty'] - q}).eq("item", it).execute()
                                    conn.table("members_data").update({"total_terima": m_data['total_terima'] + q}).eq("nama", t['user_nama']).execute()

                        elif t['tipe'] == "RETUR_BIBIT":
                            for it, q in det.items():
                                b_data = next((b for b in bibit_gdg if b['item'] == it), None)
                                if b_data:
                                    # LOGIKA JOE: Stok Gudang nambah, Bibit di tangan Joe kurang
                                    conn.table("stock_data").update({"qty": b_data['qty'] + q}).eq("item", it).execute()
                                    conn.table("members_data").update({"total_terima": m_data['total_terima'] - q}).eq("nama", t['user_nama']).execute()
                    
                    conn.table("pending_tasks").update({"status": "Approved"}).eq("id", t['id']).execute()
                    st.rerun()

# --- MENU: PENGATURAN (ANTI BLANK) ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan Database")
    
    t1, t2, t3 = st.tabs(["👤 Member", "💰 Harga Panen", "🌱 Stok Bibit"])
    
    with t1:
        st.subheader("Kelola Member")
        df_m = pd.DataFrame(members) if members else pd.DataFrame(columns=['nama', 'total_uang', 'total_kembali', 'total_terima'])
        ed_m = st.data_editor(df_m, num_rows="dynamic", key="editor_members")
        if st.button("Simpan Perubahan Member"):
            for _, r in ed_m.iterrows():
                conn.table("members_data").upsert(r.to_dict()).execute()
            st.success("Data Member diperbarui!"); st.rerun()

    with t2:
        st.subheader("Kelola Harga & Jenis Panen")
        df_p = pd.DataFrame(prices) if prices else pd.DataFrame(columns=['item', 'price'])
        ed_p = st.data_editor(df_p, num_rows="dynamic", key="editor_prices")
        if st.button("Simpan Harga"):
            for _, r in ed_p.iterrows():
                conn.table("price_data").upsert(r.to_dict()).execute()
                # Pastikan slot di gudang panen tersedia
                conn.table("stok_gudang").upsert({"item": r['item'], "stok": 0}).execute()
            st.success("Harga diperbarui!"); st.rerun()

    with t3:
        st.subheader("Kelola Stok Bibit Gudang")
        df_b = pd.DataFrame(bibit_gdg) if bibit_gdg else pd.DataFrame(columns=['item', 'qty'])
        ed_b = st.data_editor(df_b, num_rows="dynamic", key="editor_seeds")
        if st.button("Simpan Stok Bibit"):
            for _, r in ed_b.iterrows():
                conn.table("stock_data").upsert(r.to_dict()).execute()
            st.success("Stok Bibit diperbarui!"); st.rerun()
