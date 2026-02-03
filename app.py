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
    st.error("Koneksi gagal! Cek Secrets."); st.stop()

# Fungsi Load Data Fresh (Tanpa Cache untuk menghindari Blank)
def get_data(table):
    try:
        res = conn.table(table).select("*").execute()
        return res.data if res.data else []
    except: return []

# Ambil Semua Data
members = get_data("members_data")
prices = get_data("price_data")
stok_gdg = get_data("stok_gudang")
bibit_gdg = get_data("stock_data")

menu = st.sidebar.radio("MENU NAVIGASI:", ["📊 Dashboard", "📝 Setoran & Bibit", "✅ Admin Approval", "💰 Pengaturan"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring GPX")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📦 Stok Hasil Panen")
        if stok_gdg:
            for i in stok_gdg: st.info(f"{i['item']}: {i.get('stok', 0):,} Unit")
    with col2:
        st.subheader("🌱 Stok Bibit Gudang")
        if bibit_gdg:
            for i in bibit_gdg: st.success(f"{i['item']}: {i.get('qty', 0):,} Pcs")
    
    st.divider()
    st.subheader("🏆 Status Member")
    if members:
        df_m = pd.DataFrame(members)
        cols_show = ['nama', 'total_terima', 'total_kembali', 'total_uang']
        # Pastikan kolom tersedia
        for c in cols_show: 
            if c not in df_m.columns: df_m[c] = 0
        st.table(df_m[cols_show].rename(columns={
            'nama': 'Nama Member', 
            'total_terima': 'Bibit di Tangan', 
            'total_kembali': 'Total Setoran', 
            'total_uang': 'Saldo (Rp)'
        }))

# --- SETORAN & BIBIT ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan Member")
    if not members: st.warning("Isi data member dulu di Pengaturan!")
    else:
        m_name = st.selectbox("Pilih Nama Member:", [m['nama'] for m in members])
        t1, t2 = st.tabs(["🍀 Setoran Hasil Panen", "🌱 Pengambilan Bibit"])
        
        with t1:
            if not prices: st.info("Daftar harga belum diatur.")
            else:
                input_data, total_rp, rincian = {}, 0, []
                # Menampilkan form input per jenis barang
                for p in prices:
                    qty = st.number_input(f"Jumlah {p['item']} (Harga: {p['price']})", min_value=0, step=1, key=f"setor_{p['item']}")
                    if qty > 0:
                        input_data[p['item']] = qty
                        total_rp += (qty * p['price'])
                        rincian.append(f"{p['item']}: {qty}")
                
                if st.button("Kirim Laporan Setoran 🚀"):
                    if input_data:
                        conn.table("pending_tasks").insert({
                            "user_nama": m_name, "tipe": "SETOR", 
                            "detail": str(input_data), "total_nominal": total_rp, "status": "Pending"
                        }).execute()
                        requests.post(DISCORD_WEBHOOK_URL, json={"content": f"📩 **SETORAN BARU**: {m_name} | {rincian} | Total: Rp {total_rp:,}"})
                        st.success("Setoran berhasil dikirim ke Admin!")
                    else: st.error("Isi jumlah barang!")

        with t2:
            st.subheader("Kelola Bibit Member")
            aksi = st.radio("Aksi Bibit:", ["Ambil dari Gudang", "Kembalikan (Retur) ke Gudang"])
            if not bibit_gdg: st.info("Data stok bibit kosong.")
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
                        requests.post(DISCORD_WEBHOOK_URL, json={"content": f"🌱 **{tipe_b}**: {m_name} | {b_pilih}: {b_qty} Pcs"})
                        st.success(f"Laporan {aksi} terkirim!")

# --- ADMIN APPROVAL (BALIK KE PEMBAYARAN) ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    tasks = conn.table("pending_tasks").select("*").eq("status", "Pending").execute().data
    if not tasks: st.info("Antrean kosong.")
    else:
        for t in tasks:
            with st.expander(f"📌 {t['user_nama']} - {t['tipe']}"):
                st.write(f"Rincian: {t['detail']}")
                if t['total_nominal'] > 0: st.warning(f"Nilai Pembayaran: Rp {t['total_nominal']:,}")
                
                if st.button("SETUJUI & BAYAR ✅", key=f"btn_{t['id']}"):
                    det = ast.literal_eval(t['detail'])
                    m_curr = next((m for m in members if m['nama'] == t['user_nama']), None)
                    
                    if m_curr:
                        if t['tipe'] == "SETOR":
                            # Update Saldo & Unit Setoran
                            conn.table("members_data").update({
                                "total_uang": int(m_curr.get('total_uang', 0)) + t['total_nominal'],
                                "total_kembali": int(m_curr.get('total_kembali', 0)) + sum(det.values())
                            }).eq("nama", t['user_nama']).execute()
                            # Update Stok Gudang Panen
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
                                    # STOK GUDANG BERTAMBAH, BIBIT DI TANGAN MEMBER BERKURANG
                                    conn.table("stock_data").update({"qty": b_curr['qty'] + q}).eq("item", it).execute()
                                    conn.table("members_data").update({"total_terima": int(m_curr.get('total_terima', 0)) - q}).eq("nama", t['user_nama']).execute()
                    
                    conn.table("pending_tasks").update({"status": "Approved"}).eq("id", t['id']).execute()
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": f"✅ **TERBAYAR/LUNAS**: {t['user_nama']} | {t['tipe']} telah dikonfirmasi Admin."})
                    st.rerun()

# --- PENGATURAN (FIX BLANK) ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan Database")
    t1, t2, t3 = st.tabs(["👥 Member", "💵 Harga", "🌱 Stok Bibit"])
    
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
        if st.button("Simpan Stok Bibit"):
            for _, r in ed_b.iterrows(): conn.table("stock_data").upsert(r.to_dict()).execute()
            st.rerun()
