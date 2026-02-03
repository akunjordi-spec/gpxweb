import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Public Dashboard", layout="wide")

# Fungsi Load Data (Samakan dengan app.py)
def load_data_public():
    if os.path.exists('members_data.csv'):
        return pd.read_csv('members_data.csv')
    return pd.DataFrame()

def load_stok_public():
    if os.path.exists('stok_gudang.csv'):
        return pd.read_csv('stok_gudang.csv')
    return pd.DataFrame()

df_members = load_data_public()
df_stok = load_stok_public()

st.title("📊 Dashboard Publik - Game Office")

# --- BAGIAN 1: STOK GUDANG SAAT INI ---
st.subheader("📦 Stok Fisik Gudang Sekarang")
if not df_stok.empty:
    cols = st.columns(len(df_stok))
    for i, row in df_stok.iterrows():
        cols[i].metric(row['Item'], f"{row['Stok']:,} Unit")
else:
    st.info("Data stok belum tersedia.")

st.write("---")

# --- BAGIAN 2: TOP MEMBER (Statistik Terbanyak) ---
st.subheader("🏆 Statistik Member Terbaik")
c1, c2 = st.columns(2)

if not df_members.empty:
    with c1:
        st.markdown("### ⭐ Setoran Terbanyak (Saldo)")
        # Menampilkan 5 member dengan total uang (hasil setoran) tertinggi
        top_setor = df_members.nlargest(5, 'Total Uang')[['Nama', 'Total Uang']]
        st.table(top_setor)

    with c2:
        st.markdown("### 🌱 Ambil Bibit Terbanyak")
        # Menampilkan 5 member dengan total terima bibit tertinggi
        top_ambil = df_members.nlargest(5, 'Total Terima')[['Nama', 'Total Terima']]
        st.table(top_ambil)
else:
    st.warning("Belum ada data member.")

st.caption("Data diperbarui secara real-time setiap kali Admin menyetujui laporan.")
