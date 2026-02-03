import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import requests
import ast

# Konfigurasi Caching agar Web Cepat
st.set_page_config(page_title="GPX Game Office", layout="wide")

try:
    conn = st.connection("supabase", type=SupabaseConnection, 
                         url=st.secrets["SUPABASE_URL"], 
                         key=st.secrets["SUPABASE_KEY"])
    DISCORD_WEBHOOK_URL = st.secrets["MY_WEBHOOK_URL"]
except:
    st.error("Gagal koneksi database!"); st.stop()

# Fungsi Load Data dengan Cache (Biar gak lemot)
@st.cache_data(ttl=10)
def load_data(table_name):
    try:
        res = conn.table(table_name).select("*").execute()
        return res.data
    except:
        return []

# Ambil Data
members = load_data("members_data")
prices = load_data("price_data")
stok_gdg = load_data("stok_gudang")
bibit_gdg = load_data("stock_data")

# --- SIDEBAR ---
menu = st.sidebar.radio("Menu:", ["📊 Dashboard", "📝 Setoran & Bibit", "✅ Admin Approval", "💰 Pengaturan"])

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring GPX")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📦 Stok Gudang")
        if stok_gdg:
            for i in stok_gdg: st.write(f"- {i['item']}: {i['stok']:,} Unit")
    with c2:
        st.subheader("🌱 Stok Bibit")
        if bibit_gdg:
            for i in bibit_gdg: st.write(f"- {i['item']}: {i['qty']:,} Pcs")
    
    st.divider()
    st.subheader("🏆 Leaderboard (Unit Fisik)")
    if members:
        df_m = pd.DataFrame(members)
        st.table(df_m[['nama', 'total_kembali', 'total_uang']].sort_values('total_kembali', ascending=False))

# --- MENU: SETORAN & BIBIT ---
elif menu == "📝 Setoran & Bibit":
    st.title("📝 Input Kegiatan")
    if not members or not prices:
        st.warning("Isi Member & Harga di Pengaturan dulu!")
    else:
        m_name = st.selectbox("Pilih Member:", [m['nama'] for m in members])
        t1, t2 = st.tabs(["🍀 Setor Panen", "🌱 Ambil Bibit"])
        
        with t1:
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
                    st.success("Terkirim!")

        with t2:
            if bibit_gdg:
                b_pilih = st.selectbox("Pilih Bibit:", [b['item'] for b in bibit_gdg])
                b_qty = st.number_input("Jumlah Ambil:", min_value=0, step=1)
                if st.button("Kirim Ambil Bibit 🚀"):
                    conn.table("pending_tasks").insert({"user_nama": m_name, "tipe": "BIBIT", "detail": str({b_pilih: b_qty}), "total_nominal": 0}).execute()
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": f"🌱 **AMBIL BIBIT**: {m_name} | {b_pilih}: {b_qty}"})
                    st.success("Laporan Bibit Terkirim!")

# --- MENU: APPROVAL ---
elif menu == "✅ Admin Approval":
    st.title("✅ Persetujuan Admin")
    tasks = conn.table("pending_tasks").select("*").eq("status", "Pending").execute().data
    if not tasks: st.info("Tidak ada antrean.")
    else:
        for t in tasks:
            with st.expander(f"📌 {t['user_nama']} - {t['tipe']}"):
                st.write(f"Detail: {t['detail']}")
                if st.button("APPROVE ✅", key=f"bt_{t['id']}"):
                    det = ast.literal_eval(t['detail'])
                    if t['tipe'] == "SETOR":
                        # Update Saldo & Stok Panen
                        m_data = next(m for m in members if m['nama'] == t['user_nama'])
                        conn.table("members_data").update({"total_uang": m_data['total_uang'] + t['total_nominal'], "total_kembali": m_data['total_kembali'] + sum(det.values())}).eq("nama", t['user_nama']).execute()
                        for it, q in det.items():
                            s_data = next(s for s in stok_gdg if s['item'] == it)
                            conn.table("stok_gudang").update({"stok": s_data['stok'] + q}).eq("item", it).execute()
                    else:
                        # Update Bibit
                        for it, q in det.items():
                            b_data = next(b for b in bibit_gdg if b['item'] == it)
                            conn.table("stock_data").update({"qty": b_data['qty'] - q}).eq("item", it).execute()
                            m_data = next(m for m in members if m['nama'] == t['user_nama'])
                            conn.table("members_data").update({"total_terima": m_data.get('total_terima', 0) + q}).eq("nama", t['user_nama']).execute()
                    
                    conn.table("pending_tasks").update({"status": "Approved"}).eq("id", t['id']).execute()
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": f"✅ **DI-APPROVE**: {t['user_nama']} | {t['tipe']}"})
                    st.cache_data.clear(); st.rerun()

# --- MENU: PENGATURAN ---
elif menu == "💰 Pengaturan":
    st.title("⚙️ Pengaturan")
    tab1, tab2, tab3 = st.tabs(["Member", "Harga Panen", "Stok Bibit"])
    
    with tab1:
        df_m = pd.DataFrame(members) if members else pd.DataFrame(columns=['nama', 'total_uang', 'total_kembali', 'total_terima'])
        ed_m = st.data_editor(df_m, num_rows="dynamic")
        if st.button("Simpan Member"):
            for _, r in ed_m.iterrows(): conn.table("members_data").upsert(r.to_dict()).execute()
            st.cache_data.clear(); st.rerun()
            
    with tab2:
        df_p = pd.DataFrame(prices) if prices else pd.DataFrame(columns=['item', 'price'])
        ed_p = st.data_editor(df_p, num_rows="dynamic")
        if st.button("Simpan Harga"):
            for _, r in ed_p.iterrows(): 
                conn.table("price_data").upsert(r.to_dict()).execute()
                conn.table("stok_gudang").upsert({"item": r['item'], "stok": 0}).execute()
            st.cache_data.clear(); st.rerun()

    with tab3:
        df_b = pd.DataFrame(bibit_gdg) if bibit_gdg else pd.DataFrame(columns=['item', 'qty'])
        ed_b = st.data_editor(df_b, num_rows="dynamic")
        if st.button("Simpan Bibit"):
            for _, r in ed_b.iterrows(): conn.table("stock_data").upsert(r.to_dict()).execute()
            st.cache_data.clear(); st.rerun()
