import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import requests
import ast

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Game Office Pro - Database Mode", layout="wide", page_icon="🏢")

# --- 2. KONEKSI DATABASE & WEBHOOK ---
try:
    # Koneksi otomatis menggunakan st.connection (mengambil dari Secrets)
    conn = st.connection("supabase", type=SupabaseConnection)
    DISCORD_WEBHOOK_URL = st.secrets["MY_WEBHOOK_URL"]
except Exception as e:
    st.error("⚠️ Konfigurasi Secrets tidak lengkap! Pastikan URL, Key, dan Webhook sudah diisi.")
    st.stop()

# --- 3. FUNGSI HELPER ---
def send_to_discord(message):
    if DISCORD_WEBHOOK_URL:
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        except:
            pass

def refresh_data():
    m = conn.query("*", table="members_data").execute()
    s = conn.query("*", table="stok_gudang").execute()
    b = conn.query("*", table="stock_data").execute()
    p = conn.query("*", table="price_data").execute()
    return m.data, s.data, b.data, p.data

# Ambil data awal
members_data, stok_data, bibit_data, price_data = refresh_data()

# --- 4. SIDEBAR MENU ---
st.sidebar.title("🏢 KANTOR PUSAT")
menu = st.sidebar.selectbox("MENU UTAMA", 
    ["📊 Dashboard", "📝 Input Member", "✅ Approval & Bayar", "⚙️ Stock Opname", "💰 Atur Harga & Member"]
)

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring Dashboard (Real-time)")
    
    # Ringkasan Stok
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🌱 Stok Bibit")
        if bibit_data:
            cols_b = st.columns(len(bibit_data))
            for i, item in enumerate(bibit_data):
                cols_b[i].metric(item['item'], f"{item['qty']:,} Pcs")
            
    with c2:
        st.subheader("📦 Stok Gudang")
        if stok_data:
            cols_s = st.columns(len(stok_data))
            for i, item in enumerate(stok_data):
                cols_s[i].metric(item['item'], f"{item['stok']:,} Unit")

    st.write("---")
    
    # Leaderboard
    st.subheader("🏆 Leaderboard Member")
    l1, l2 = st.columns(2)
    df_m = pd.DataFrame(members_data)
    
    with l1:
        st.markdown("### ⭐ Penyetor Terbanyak (Unit Fisik)")
        if not df_m.empty:
            top_setor = df_m.nlargest(5, 'total_kembali')[['nama', 'total_kembali']]
            st.dataframe(top_setor.rename(columns={'nama': 'Nama', 'total_kembali': 'Total Unit'}), 
                         use_container_width=True, hide_index=True)
            
    with l2:
        st.markdown("### 🌱 Pengambil Bibit Terbanyak")
        if not df_m.empty:
            top_ambil = df_m.nlargest(5, 'total_terima')[['nama', 'total_terima']]
            st.dataframe(top_ambil.rename(columns={'nama': 'Nama', 'total_terima': 'Total Bibit'}), 
                         use_container_width=True, hide_index=True)

# --- MENU: INPUT MEMBER ---
elif menu == "📝 Input Member":
    st.title("📝 Form Input Member")
    m_name = st.selectbox("Pilih Member", sorted([m['nama'] for m in members_data]))
    t1, t2 = st.tabs(["🍀 Setoran Hasil", "🌱 Ambil Bibit"])
    
    with t1:
        prices = {p['item']: p['price'] for p in price_data}
        cols = st.columns(3)
        input_qty, total_nom, rincian_discord = {}, 0, []
        
        for i, (item, prc) in enumerate(prices.items()):
            q = cols[i % 3].number_input(f"Jumlah {item}", min_value=0, step=1, key=f"in_{item}")
            if q > 0:
                input_qty[item] = q
                total_nom += (q * prc)
                rincian_discord.append(f"{item} : {q:,}")
        
        if st.button("Kirim Laporan Setoran"):
            if input_qty:
                conn.table("pending_tasks").insert({
                    "user_nama": m_name, "tipe": "SETOR", "detail": str(input_qty),
                    "total_nominal": total_nom, "status": "Pending"
                }).execute()
                
                # Format Discord Request
                tgl = datetime.now().strftime("%d/%m/%y")
                msg = f"**SETORAN {tgl}**\n\n**{m_name}**\n" + "\n".join(rincian_discord) + f"\n**TOTAL : {total_nom:,}**"
                send_to_discord(msg)
                st.success("Laporan terkirim!")
            else:
                st.warning("Isi jumlah barang!")

    with t2:
        bbt_item = st.selectbox("Pilih Bibit", [b['item'] for b in bibit_data])
        jml_ambil = st.number_input("Jumlah Ambil", min_value=1, step=1)
        if st.button("Ajukan Ambil Bibit"):
            conn.table("pending_tasks").insert({
                "user_nama": m_name, "tipe": "AMBIL", "detail": f"{bbt_item}:{jml_ambil}",
                "total_nominal": 0, "status": "Pending"
            }).execute()
            st.success("Permintaan bibit dikirim!")

# --- MENU: APPROVAL ---
elif menu == "✅ Approval & Bayar":
    st.title("✅ Persetujuan & Pembayaran")
    res_pending = conn.query("*", table="pending_tasks").eq("status", "Pending").execute()
    
    if not res_pending.data:
        st.info("Tidak ada antrean laporan.")
    else:
        for task in res_pending.data:
            with st.expander(f"{task['user_nama']} - {task['tipe']}"):
                st.write(f"Detail: {task['detail']}")
                if st.button("KONFIRMASI ✅", key=f"btn_{task['id']}"):
                    if task['tipe'] == "SETOR":
                        # Gunakan literal_eval agar aman mengubah string dict ke dict
                        details = ast.literal_eval(task['detail'])
                        total_fisik = sum(details.values())
                        
                        m_curr = next(m for m in members_data if m['nama'] == task['user_nama'])
                        conn.table("members_data").update({
                            "total_uang": m_curr['total_uang'] + task['total_nominal'],
                            "total_kembali": m_curr['total_kembali'] + total_fisik
                        }).eq("nama", task['user_nama']).execute()
                        
                        for it, qty in details.items():
                            s_curr = next(s for s in stok_data if s['item'] == it)
                            conn.table("stok_gudang").update({"stok": s_curr['stok'] + qty}).eq("item", it).execute()
                        
                        send_to_discord(f"✅ **DIBAYAR:** {task['user_nama']} senilai Rp {task['total_nominal']:,}")

                    elif task['tipe'] == "AMBIL":
                        it_b, qty_b = task['detail'].split(":")
                        qty_b = int(qty_b)
                        m_curr = next(m for m in members_data if m['nama'] == task['user_nama'])
                        conn.table("members_data").update({"total_terima": m_curr['total_terima'] + qty_b}).eq("nama", task['user_nama']).execute()
                        b_curr = next(b for b in bibit_data if b['item'] == it_b)
                        conn.table("stock_data").update({"qty": b_curr['qty'] - qty_b}).eq("item", it_b).execute()

                    conn.table("pending_tasks").update({"status": "Approved"}).eq("id", task['id']).execute()
                    st.rerun()

# --- MENU: STOCK OPNAME ---
elif menu == "⚙️ Stock Opname":
    st.title("⚙️ Koreksi Stok (Admin)")
    tab_s, tab_b = st.tabs(["📦 Stok Barang", "🌱 Stok Bibit"])
    with tab_s:
        item_sel = st.selectbox("Pilih Barang", [s['item'] for s in stok_data])
        qty_new = st.number_input("Stok Baru", min_value=0)
        if st.button("Update Stok Gudang"):
            conn.table("stok_gudang").update({"stok": qty_new}).eq("item", item_sel).execute()
            st.success("Stok diperbarui!"); st.rerun()
    with tab_b:
        bibit_sel = st.selectbox("Pilih Bibit", [b['item'] for b in bibit_data])
        qty_b_new = st.number_input("Stok Bibit Baru", min_value=0)
        if st.button("Update Stok Bibit"):
            conn.table("stock_data").update({"qty": qty_b_new}).eq("item", bibit_sel).execute()
            st.success("Stok bibit diperbarui!"); st.rerun()

# --- MENU: ATUR HARGA & MEMBER ---
elif menu == "💰 Atur Harga & Member":
    st.title("⚙️ Pengaturan Database")
    t1, t2 = st.tabs(["💰 Harga & Barang", "👥 Member"])
    with t1:
        st.subheader("Inventory & Harga Beli")
        st.dataframe(pd.DataFrame(price_data), use_container_width=True, hide_index=True)
        with st.form("add_item"):
            n_item = st.text_input("Nama Barang Baru (Contoh: DAUN)").upper()
            h_item = st.number_input("Harga Beli (Rp)", min_value=0)
            if st.form_submit_button("Simpan Barang"):
                conn.table("price_data").upsert({"item": n_item, "price": h_item}).execute()
                conn.table("stok_gudang").upsert({"item": n_item, "stok": 0}).execute()
                st.rerun()
    with t2:
        st.subheader("Manajemen Member")
        edited_m = st.data_editor(pd.DataFrame(members_data), num_rows="dynamic", use_container_width=True)
        if st.button("Simpan Perubahan Member"):
            for _, row in edited_m.iterrows():
                # Hapus ID agar tidak konflik saat upsert jika id kosong
                d = row.to_dict()
                conn.table("members_data").upsert(d).execute()
            st.success("Data Member Diperbarui!"); st.rerun()
