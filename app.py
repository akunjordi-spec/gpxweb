import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Game Office Pro Manager", layout="wide", page_icon="🏢")

# --- 2. DAFTAR MEMBER DEFAULT ---
DEFAULT_NAMES = [
    "JOE JETZY", "REXY NUGROHO", "ALEXANDRO JETZY", "VAREL", "NOAH", 
    "JAMAL", "BANGPOK", "KARELA", "HANS", "AMAT LINCOLN", 
    "JOHAN CUKARDELENG", "FRANK CUKARDELENG", "MAX EL STEIN", "BIG BOS", 
    "ARUL", "REY", "CHEONG", "VICKTOR", "MARO", "SUGGEW", "NUSA", "WAHAB", "FRIOREN"
]

# --- 3. FUNGSI DATABASE (LOAD & SAVE) ---
def save_all():
    st.session_state.members.to_csv('members_data.csv', index=False)
    pd.DataFrame(list(st.session_state.stock_bibit.items()), columns=['Item', 'Qty']).to_csv('stock_data.csv', index=False)
    pd.DataFrame(list(st.session_state.prices.items()), columns=['Item', 'Price']).to_csv('price_data.csv', index=False)
    pd.DataFrame(list(st.session_state.stok_gudang.items()), columns=['Item', 'Stok']).to_csv('stok_gudang.csv', index=False)
    st.session_state.pending_tasks.to_csv('pending_tasks.csv', index=False)
    st.session_state.sales_history.to_csv('sales_history.csv', index=False)

def load_data():
    # Load atau Inisialisasi Members
    if os.path.exists('members_data.csv'):
        st.session_state.members = pd.read_csv('members_data.csv')
        # Pastikan kolom 'Total Uang' ada untuk menghindari KeyError
        if 'Total Uang' not in st.session_state.members.columns:
            st.session_state.members['Total Uang'] = 0
    else:
        st.session_state.members = pd.DataFrame([{'Nama': n, 'Total Terima': 0, 'Total Kembali': 0, 'Total Uang': 0} for n in DEFAULT_NAMES])

    # Load Antrean Approval
    if os.path.exists('pending_tasks.csv'):
        st.session_state.pending_tasks = pd.read_csv('pending_tasks.csv')
    else:
        st.session_state.pending_tasks = pd.DataFrame(columns=['ID', 'User', 'Tipe', 'Detail', 'Status', 'Waktu', 'TotalNominal', 'SisaBibit'])

    # Load History Penjualan
    if os.path.exists('sales_history.csv'):
        st.session_state.sales_history = pd.read_csv('sales_history.csv')
    else:
        st.session_state.sales_history = pd.DataFrame(columns=['Waktu', 'Pembeli', 'Item', 'Qty', 'HargaJual', 'Total'])

    # Load Stok Gudang (Hasil Panen)
    if os.path.exists('stok_gudang.csv'):
        df = pd.read_csv('stok_gudang.csv')
        st.session_state.stok_gudang = dict(zip(df.Item, df.Stok))
    else: 
        st.session_state.stok_gudang = {"CENGKEH": 0, "AKAR": 0, "DAUN": 0, "RANTING": 0}

    # Load Harga Barang
    if os.path.exists('price_data.csv'):
        df = pd.read_csv('price_data.csv')
        st.session_state.prices = dict(zip(df.Item, df.Price))
    else: 
        st.session_state.prices = {"CENGKEH": 100, "AKAR": 50, "DAUN": 30, "RANTING": 20}
    
    # Load Stok Bibit Kantor
    if os.path.exists('stock_data.csv'):
        df = pd.read_csv('stock_data.csv')
        st.session_state.stock_bibit = dict(zip(df.Item, df.Qty))
    else: 
        st.session_state.stock_bibit = {"BIBIT CENGKEH": 0}

# --- 4. INISIALISASI APLIKASI ---
if 'members' not in st.session_state:
    load_data()

# --- 5. SIDEBAR NAVIGATION ---
st.sidebar.title("🏢 KANTOR PUSAT")
menu = st.sidebar.selectbox("MENU UTAMA", 
    ["📊 Dashboard & Finansial", "📝 Input Member", "✅ Approval Admin", "💸 Penjualan Luar", "⚙️ Stock Opname", "💰 Atur Harga & Member"])

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard & Finansial":
    st.title("📊 Status Kantor & Stok")
    
    # Grid Stok Gudang
    st.subheader("📦 Stok Fisik Gudang")
    cols = st.columns(4)
    for i, (item, qty) in enumerate(st.session_state.stok_gudang.items()):
        cols[i % 4].metric(item, f"{qty:,} Unit")
    
    st.write("---")
    
    c1, c2 = st.columns(2)
    with c1:
        total_hutang = st.session_state.members['Total Uang'].sum()
        st.metric("Total Hutang ke Member", f"Rp {total_hutang:,}")
        st.subheader("🏆 Saldo Member")
        st.dataframe(st.session_state.members.sort_values(by="Total Uang", ascending=False)[['Nama', 'Total Uang']], use_container_width=True, hide_index=True)
    
    with c2:
        total_sales = st.session_state.sales_history['Total'].sum()
        st.metric("Total Penjualan Luar", f"Rp {total_sales:,}")
        st.subheader("📜 Riwayat Penjualan")
        st.dataframe(st.session_state.sales_history.tail(10), use_container_width=True, hide_index=True)

# --- MENU: INPUT MEMBER ---
elif menu == "📝 Input Member":
    st.title("📝 Input Laporan Member")
    m_name = st.selectbox("Pilih Nama Member", st.session_state.members['Nama'])
    t_setor, t_ambil = st.tabs(["Setoran Hasil", "Ambil Bibit"])
    
    with t_setor:
        detail_setor = []
        total_nom = 0
        cols = st.columns(3)
        for i, (item, prc) in enumerate(st.session_state.prices.items()):
            q = cols[i % 3].number_input(f"Jumlah {item}", min_value=0, key=f"s_{item}")
            if q > 0:
                detail_setor.append(f"{item}:{q}")
                total_nom += (q * prc)
        
        v_kembali = st.number_input("Bibit Kembali (Sisa)", min_value=0)
        st.markdown(f"### Estimasi Terima: **Rp {total_nom:,}**")
        
        if st.button("Kirim Laporan"):
            if detail_setor:
                new_task = pd.DataFrame([{
                    'ID': datetime.now().timestamp(), 'User': m_name, 'Tipe': 'SETOR',
                    'Detail': ",".join(detail_setor), 'TotalNominal': total_nom,
                    'SisaBibit': v_kembali, 'Status': 'Pending', 'Waktu': datetime.now().strftime("%d/%m %H:%M")
                }])
                st.session_state.pending_tasks = pd.concat([st.session_state.pending_tasks, new_task], ignore_index=True)
                save_all()
                st.success("Laporan terkirim ke Admin!")

    with t_ambil:
        bbt = st.selectbox("Pilih Bibit", list(st.session_state.stock_bibit.keys()))
        jml = st.number_input("Jumlah Ambil", min_value=1)
        if st.button("Ajukan Ambil"):
            new_task = pd.DataFrame([{
                'ID': datetime.now().timestamp(), 'User': m_name, 'Tipe': 'AMBIL',
                'Detail': f"{bbt}:{jml}", 'TotalNominal': 0, 'SisaBibit': 0,
                'Status': 'Pending', 'Waktu': datetime.now().strftime("%d/%m %H:%M")
            }])
            st.session_state.pending_tasks = pd.concat([st.session_state.pending_tasks, new_task], ignore_index=True)
            save_all()
            st.success("Permintaan terkirim!")

# --- MENU: APPROVAL ---
elif menu == "✅ Approval Admin":
    st.title("✅ Persetujuan Transaksi")
    pending = st.session_state.pending_tasks[st.session_state.pending_tasks['Status'] == 'Pending']
    
    if pending.empty:
        st.info("Tidak ada transaksi menunggu.")
    else:
        for idx, row in pending.iterrows():
            with st.expander(f"{row['User']} - {row['Tipe']} ({row['Waktu']})"):
                st.write(f"**Detail:** {row['Detail']}")
                if row['Tipe'] == 'SETOR':
                    st.write(f"**Uang:** Rp {row['TotalNominal']:,} | **Balik Bibit:** {row['SisaBibit']}")
                
                c1, c2 = st.columns(2)
                if c1.button("APPROVE ✅", key=f"app_{idx}"):
                    midx = st.session_state.members[st.session_state.members['Nama'] == row['User']].index[0]
                    if row['Tipe'] == 'SETOR':
                        # Update Stok Gudang & Saldo Member
                        for i in row['Detail'].split(","):
                            name, val = i.split(":")
                            st.session_state.stok_gudang[name] = st.session_state.stok_gudang.get(name, 0) + int(val)
                        st.session_state.members.at[midx, 'Total Uang'] += row['TotalNominal']
                        st.session_state.members.at[midx, 'Total Kembali'] += row['SisaBibit']
                    elif row['Tipe'] == 'AMBIL':
                        # Update Stok Bibit & Terima Member
                        name, val = row['Detail'].split(":")
                        st.session_state.stock_bibit[name] -= int(val)
                        st.session_state.members.at[midx, 'Total Terima'] += int(val)
                    
                    st.session_state.pending_tasks.at[idx, 'Status'] = 'Approved'
                    save_all()
                    st.rerun()
                if c2.button("REJECT ❌", key=f"rej_{idx}"):
                    st.session_state.pending_tasks.at[idx, 'Status'] = 'Rejected'
                    save_all()
                    st.rerun()

# --- MENU: PENJUALAN LUAR ---
elif menu == "💸 Penjualan Luar":
    st.title("💸 Jual Barang ke Luar")
    with st.form("jual_luar"):
        pembeli = st.text_input("Nama Pembeli / Pasar")
        item_j = st.selectbox("Pilih Barang", list(st.session_state.stok_gudang.keys()))
        col1, col2 = st.columns(2)
        q_j = col1.number_input("Jumlah Jual", min_value=1)
        h_j = col2.number_input("Harga Jual Satuan", min_value=0)
        
        if st.form_submit_button("Konfirmasi Jual"):
            if st.session_state.stok_gudang.get(item_j, 0) >= q_j:
                st.session_state.stok_gudang[item_j] -= q_j
                new_s = pd.DataFrame([{'Waktu': datetime.now().strftime("%Y-%m-%d %H:%M"), 'Pembeli': pembeli, 'Item': item_j, 'Qty': q_j, 'HargaJual': h_j, 'Total': q_j * h_j}])
                st.session_state.sales_history = pd.concat([st.session_state.sales_history, new_s], ignore_index=True)
                save_all()
                st.success(f"Berhasil menjual {q_j} {item_j}!")
                st.rerun()
            else: st.error("Stok gudang tidak cukup!")

# --- MENU: STOCK OPNAME ---
elif menu == "⚙️ Stock Opname":
    st.title("⚙️ Koreksi Stok (Stock Opname)")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Koreksi Hasil Panen")
        it_so = st.selectbox("Barang", list(st.session_state.stok_gudang.keys()), key="so_p")
        qt_so = st.number_input("Stok Sebenarnya", min_value=0, key="so_q")
        if st.button("Set Stok Gudang"):
            st.session_state.stok_gudang[it_so] = qt_so
            save_all()
            st.success("Stok Gudang diperbarui!")
    with c2:
        st.subheader("Koreksi Bibit")
        it_b = st.selectbox("Jenis Bibit", list(st.session_state.stock_bibit.keys()), key="so_b")
        qt_b = st.number_input("Stok Sebenarnya", min_value=0, key="so_bq")
        if st.button("Set Stok Bibit"):
            st.session_state.stock_bibit[it_b] = qt_b
            save_all()
            st.success("Stok Bibit diperbarui!")

# --- MENU: PENGATURAN ---
elif menu == "💰 Atur Harga & Member":
    st.title("⚙️ Pengaturan Dasar")
    tab_harga, tab_member = st.tabs(["Harga Barang", "Data Member"])
    with tab_harga:
        n_baru = st.text_input("Nama Barang Baru").upper()
        h_baru = st.number_input("Harga Satuan", min_value=0)
        if st.button("Tambah/Update Harga"):
            st.session_state.prices[n_baru] = h_baru
            if n_baru not in st.session_state.stok_gudang: st.session_state.stok_gudang[n_baru] = 0
            save_all()
            st.rerun()
        st.table(pd.DataFrame(list(st.session_state.prices.items()), columns=['Barang', 'Harga']))
    with tab_member:
        # Menghapus kolom 'Pass' jika ada untuk menghindari error tampilan editor
        df_display = st.session_state.members.copy()
        edited_df = st.data_editor(df_display, use_container_width=True, num_rows="dynamic")
        if st.button("Simpan Perubahan Member"):
            st.session_state.members = edited_df
            save_all()
            st.success("Data Member disimpan!")