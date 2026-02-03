import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Marketplace & Stock Dashboard", layout="wide", page_icon="📈")

# --- FUNGSI LOAD DATA (Sinkron dengan Database Utama) ---
def load_csv(file_name):
    if os.path.exists(file_name):
        return pd.read_csv(file_name)
    return pd.DataFrame()

# Load semua data yang diperlukan
df_members = load_csv('members_data.csv')
df_stok_gudang = load_csv('stok_gudang.csv') # Inventory Siap Jual
df_stok_bibit = load_csv('stock_data.csv')   # Stok Bibit

st.title("🏛️ Game Office Public Market")
st.markdown("Halaman ini menampilkan ketersediaan barang di gudang kami untuk para Buyer.")

# --- BAGIAN 1: STOK INVENTORY UNTUK BUYER ---
st.write("---")
st.subheader("📦 Inventory Siap Jual (Ready Stock)")
st.info("Informasi ketersediaan barang hasil olahan member kami.")

if not df_stok_gudang.empty:
    # Menampilkan stok gudang dalam bentuk kolom metric yang menarik
    cols_inv = st.columns(len(df_stok_gudang))
    for i, row in df_stok_gudang.iterrows():
        cols_inv[i].metric(
            label=f"Stok {row['Item']}", 
            value=f"{int(row['Stok']):,} Unit",
            delta="Tersedia"
        )
else:
    st.warning("Maaf, stok inventory saat ini sedang kosong.")

# --- BAGIAN 2: STOK BIBIT ---
st.write("---")
st.subheader("🌱 Ketersediaan Bibit")
if not df_stok_bibit.empty:
    cols_bibit = st.columns(len(df_stok_bibit))
    for i, row in df_stok_bibit.iterrows():
        cols_bibit[i].metric(
            label=row['Item'], 
            value=f"{int(row['Qty']):,} Pcs"
        )
else:
    st.info("Data stok bibit tidak tersedia.")

st.write("---")

# --- BAGIAN 3: LEADERBOARD MEMBER (TOP PERFORMANCES) ---
st.subheader("🏆 Member Hall of Fame")
st.markdown("Apresiasi untuk member paling aktif dalam operasional kantor.")

c1, c2 = st.columns(2)

if not df_members.empty:
    with c1:
        st.markdown("#### ⭐ Top Penyetor (Hasil Olahan)")
        # Menampilkan 5 member dengan penghasilan tertinggi
        top_setor = df_members.nlargest(5, 'Total Uang')[['Nama', 'Total Uang']]
        top_setor.columns = ['Nama Member', 'Total Hasil (Rp)']
        st.dataframe(top_setor, use_container_width=True, hide_index=True)

    with c2:
        st.markdown("#### 🌱 Top Petani (Pengambil Bibit)")
        # Menampilkan 5 member dengan pengambilan bibit terbanyak
        top_ambil = df_members.nlargest(5, 'Total Terima')[['Nama', 'Total Terima']]
        top_ambil.columns = ['Nama Member', 'Bibit Diterima (Pcs)']
        st.dataframe(top_ambil, use_container_width=True, hide_index=True)
else:
    st.warning("Belum ada data aktivitas member.")

# --- FOOTER ---
st.write("---")
st.caption(f"Update Terakhir: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}")
st.caption("Hubungi Admin Kantor untuk melakukan pembelian besar (Bulk Order).")
