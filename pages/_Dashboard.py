import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Marketplace & Stock Dashboard", layout="wide", page_icon="📈")

# --- KONFIGURASI GOOGLE SHEETS (OPSIONAL) ---
# Jika ingin pakai Google Sheets, masukkan link CSV publish di sini:
# Cara: File > Share > Publish to web > Pilih Sheet > Format CSV > Copy Linknya
# GANTI LINK DI BAWAH INI JIKA SUDAH ADA
SHEET_MEMBERS = "members_data.csv" # Bisa diganti link https://docs.google.com/...
SHEET_STOK = "stok_gudang.csv"
SHEET_BIBIT = "stock_data.csv"

def load_data(source):
    try:
        if source.startswith("http"):
            return pd.read_csv(source)
        elif os.path.exists(source):
            return pd.read_csv(source)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

df_members = load_data(SHEET_MEMBERS)
df_stok_gudang = load_data(SHEET_STOK)
df_stok_bibit = load_data(SHEET_BIBIT)

st.title("🏛️ Game Office Public Market")

# --- BAGIAN 1: STOK INVENTORY UNTUK BUYER ---
st.subheader("📦 Inventory Siap Jual (Ready Stock)")
if not df_stok_gudang.empty:
    cols_inv = st.columns(len(df_stok_gudang))
    for i, row in df_stok_gudang.iterrows():
        cols_inv[i].metric(label=f"{row['Item']}", value=f"{int(row['Stok']):,} Unit")
else:
    st.warning("Stok inventory kosong.")

# --- BAGIAN 2: STOK BIBIT ---
st.write("---")
st.subheader("🌱 Ketersediaan Bibit")
if not df_stok_bibit.empty:
    cols_bibit = st.columns(len(df_stok_bibit))
    for i, row in df_stok_bibit.iterrows():
        cols_bibit[i].metric(label=row['Item'], value=f"{int(row['Qty']):,} Pcs")

st.write("---")

# --- BAGIAN 3: LEADERBOARD MEMBER ---
st.subheader("🏆 Member Hall of Fame")

c1, c2 = st.columns(2)

if not df_members.empty:
    with c1:
        st.markdown("#### ⭐ Top Penyetor (Jumlah Hasil Terbanyak)")
        # LOGIKA BARU: Diambil dari 'Total Kembali' (Atau kolom jumlah barang)
        # Kita gunakan 'Total Kembali' sebagai indikator jumlah fisik yang disetor
        top_fisik = df_members.nlargest(5, 'Total Kembali')[['Nama', 'Total Kembali']]
        top_fisik.columns = ['Nama Member', 'Total Setoran (Unit)']
        st.dataframe(top_fisik, use_container_width=True, hide_index=True)

    with c2:
        st.markdown("#### 🌱 Top Petani (Pengambil Bibit)")
        top_ambil = df_members.nlargest(5, 'Total Terima')[['Nama', 'Total Terima']]
        top_ambil.columns = ['Nama Member', 'Bibit Diterima (Pcs)']
        st.dataframe(top_ambil, use_container_width=True, hide_index=True)

st.caption(f"Update Terakhir: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}")
