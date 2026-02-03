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
    # Load Members
    if os.path.exists('members_data.csv'):
        st.session_state.members = pd.read_csv('members_data.csv')
    else:
        st.session_state.members = pd.DataFrame([{'Nama': n, 'Total Terima': 0, 'Total Kembali': 0, 'Total Uang': 0} for n in DEFAULT_NAMES])

    # Load Antrean Approval
    if os.path.exists('pending_tasks.csv'):
        st.session_state.pending_tasks = pd.read_csv('pending_tasks.csv')
    else:
        st.session_state.pending_tasks = pd.DataFrame(columns=['ID', 'User', 'Tipe', 'Detail', 'Status', 'Waktu', 'TotalNominal', 'SisaBibit'])

    # Load History Penjualan Luar
    if os.path.exists('sales_history.csv'):
        st.session_state.sales_history = pd.read_csv('sales_history.csv')
    else:
        st.session_state.sales_history = pd.DataFrame(columns=['Waktu', 'Pembeli', 'Item', 'Qty', 'HargaJual', 'Total'])

    # Load Harga & Stok Barang (Dinamis: Bisa Susu, Kulit, dll)
    if os.path.exists('price_data.csv'):
        df_p = pd.read_csv('price_data.csv')
        st.session_state.prices = dict(zip(df_p.Item, df_p.Price))
    else:
        st.session_state.prices = {"CENGKEH": 100, "AKAR": 50, "SUSU": 200, "KULIT": 150}

    if os.path.exists('stok_gudang.csv'):
        df_s = pd.read_csv('stok_gudang.csv')
        st.session_state.stok_gudang = dict(zip(df_s.Item, df_s.Stok))
    else:
        st.session_state.stok_gudang = {k: 0 for k in st.session_state.prices.keys()}

    # Load Stok Bibit
    if os.path.exists('stock_data.csv'):
        df_b = pd.read_csv('stock_data.csv')
        st.session_state.stock_bibit = dict(zip(df_b.Item, df_b.Qty))
    else:
        st.session_state.stock_bibit = {"BIBIT CENGKEH": 1000}

# --- 4. INISIALISASI ---
if 'members' not in st.session_state:
    load_data()

# --- 5. SIDEBAR MENU ---
st.sidebar.title("🏢 KANTOR PUSAT")
menu = st.sidebar.selectbox("MENU UTAMA", 
    ["📊 Dashboard & Finansial", "📝 Form Input Member", "✅ Approval Admin", "💸 Penjualan Luar", "⚙️ Stock Opname", "💰 Atur Harga & Member"])

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard & Finansial":
    st.title("📊 Status Gudang & Finansial")
    
    st.subheader("📦 Stok Fisik Gudang (Siap Jual)")
    if st.session_state.stok_gudang:
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
        st.metric("Total Pemasukan Kantor", f"Rp {total_sales:,}")
        st.subheader("Riwayat Penjualan Keluar")
        st.dataframe(st.session_state.sales_history.tail(10), use_container_width=True, hide_index=True)

# --- MENU: FORM INPUT MEMBER ---
elif menu == "📝 Form Input Member":
    st.title("📝 Form Setoran & Ambil Bibit")
    m_name = st.selectbox("Pilih Nama Member", st.session_state.members['Nama'])
    t1, t2 = st.tabs(["Setoran Hasil (Tanaman/Susu/Kulit)", "Ambil Bibit"])
    
    with t1:
        detail_setor = []
        total_nom = 0
        st.write("### Masukkan Barang yang Disetor:")
        cols = st.columns(3)
        for i, (item, prc) in enumerate(st.session_state.prices.items()):
            q = cols[i % 3].number_input(f"Jumlah {item}", min_value=0, key=f"s_{item}", step=1)
            if q > 0:
                detail_setor.append(f"{item}:{q}")
                total_nom += (q * prc)
        
        v_kembali = st.number_input("Bibit Sisa yang Dikembalikan", min_value=0)
        st.info(f"💰 Estimasi Uang: **Rp {total_nom:,}**")
        
        if st.button("Kirim Laporan"):
            if detail_setor:
                new_t = pd.DataFrame([{'ID': datetime.now().timestamp(), 'User': m_name, 'Tipe': 'SETOR', 'Detail': ",".join(detail_setor), 'TotalNominal': total_nom, 'SisaBibit': v_kembali, 'Status': 'Pending', 'Waktu': datetime.now().strftime("%d/%m %H:%M")}])
                st.session_state.pending_tasks = pd.concat([st.session_state.pending_tasks, new_t], ignore_index=True)
                save_all()
                st.success("Laporan terkirim! Menunggu approval Admin.")

    with t2:
        bbt = st.selectbox("Pilih Bibit", list(st.session_state.stock_bibit.keys()))
        jml = st.number_input("Jumlah Ambil", min_value=1)
        if st.button("Ajukan Ambil Bibit"):
            new_t = pd.DataFrame([{'ID': datetime.now().timestamp(), 'User': m_name, 'Tipe': 'AMBIL', 'Detail': f"{bbt}:{jml}", 'TotalNominal': 0, 'SisaBibit': 0, 'Status': 'Pending', 'Waktu': datetime.now().strftime("%d/%m %H:%M")}])
            st.session_state.pending_tasks = pd.concat([st.session_state.pending_tasks, new_t], ignore_index=True)
            save_all()
            st.success("Permintaan terkirim!")

# --- MENU: APPROVAL ---
elif menu == "✅ Approval Admin":
    st.title("✅ Konfirmasi Laporan")
    pending = st.session_state.pending_tasks[st.session_state.pending_tasks['Status'] == 'Pending']
    if pending.empty:
        st.info("Tidak ada transaksi menunggu.")
    else:
        for idx, row in pending.iterrows():
            with st.expander(f"{row['User']} - {row['Tipe']} ({row['Waktu']})"):
                st.write(f"**Detail:** {row['Detail']}")
                if row['Tipe'] == 'SETOR':
                    st.write(f"**Total Uang:** Rp {row['TotalNominal']:,}")
                
                c1, c2 = st.columns(2)
                if c1.button("APPROVE ✅", key=f"ok_{idx}"):
                    midx = st.session_state.members[st.session_state.members['Nama'] == row['User']].index[0]
                    if row['Tipe'] == 'SETOR':
                        for i in row['Detail'].split(","):
                            n, v = i.split(":")
                            st.session_state.stok_gudang[n] = st.session_state.stok_gudang.get(n, 0) + int(v)
                        st.session_state.members.at[midx, 'Total Uang'] += row['TotalNominal']
                        st.session_state.members.at[midx, 'Total Kembali'] += row['SisaBibit']
                    elif row['Tipe'] == 'AMBIL':
                        n, v = row['Detail'].split(":")
                        st.session_state.stock_bibit[n] -= int(v)
                        st.session_state.members.at[midx, 'Total Terima'] += int(v)
                    
                    st.session_state.pending_tasks.at[idx, 'Status'] = 'Approved'
                    save_all(); st.rerun()
                if c2.button("REJECT ❌", key=f"no_{idx}"):
                    st.session_state.pending_tasks.at[idx, 'Status'] = 'Rejected'
                    save_all(); st.rerun()

# --- MENU: PENJUALAN LUAR ---
elif menu == "💸 Penjualan Luar":
    st.title("💸 Penjualan ke Luar (NPC/Pasar)")
    with st.form("jual_luar"):
        pembeli = st.text_input("Nama Pembeli")
        item_j = st.selectbox("Barang Gudang", list(st.session_state.stok_gudang.keys()))
        col1, col2 = st.columns(2)
        q_j = col1.number_input("Jumlah", min_value=1)
        h_j = col2.number_input("Harga Jual Satuan", min_value=0)
        if st.form_submit_button("Proses Jual"):
            if st.session_state.stok_gudang.get(item_j, 0) >= q_j:
                st.session_state.stok_gudang[item_j] -= q_j
                new_s = pd.DataFrame([{'Waktu': datetime.now().strftime("%d/%m %H:%M"), 'Pembeli': pembeli, 'Item': item_j, 'Qty': q_j, 'HargaJual': h_j, 'Total': q_j * h_j}])
                st.session_state.sales_history = pd.concat([st.session_state.sales_history, new_s], ignore_index=True)
                save_all(); st.success("Terjual!"); st.rerun()
            else: st.error("Stok Gudang Tidak Cukup!")

# --- MENU: STOCK OPNAME ---
elif menu == "⚙️ Stock Opname":
    st.title("⚙️ Koreksi Stok")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Koreksi Stok Gudang")
        it_s = st.selectbox("Barang", list(st.session_state.stok_gudang.keys()), key="so1")
        qt_s = st.number_input("Fisik Sebenarnya", min_value=0, key="so2")
        if st.button("Update Gudang"):
            st.session_state.stok_gudang[it_s] = qt_s
            save_all(); st.success("Update Berhasil!")
    with c2:
        st.subheader("Koreksi Stok Bibit")
        it_b = st.selectbox("Bibit", list(st.session_state.stock_bibit.keys()), key="so3")
        qt_b = st.number_input("Fisik Sebenarnya", min_value=0, key="so4")
        if st.button("Update Bibit"):
            st.session_state.stock_bibit[it_b] = qt_b
            save_all(); st.success("Update Berhasil!")

# --- MENU: PENGATURAN HARGA & MEMBER ---
elif menu == "💰 Atur Harga & Member":
    st.title("⚙️ Pengaturan Dasar")
    t1, t2 = st.tabs(["💰 Daftar Harga & Barang", "👥 Manajemen Member"])
    
    with t1:
        st.subheader("Tambah/Edit Barang & Harga")
        col_a, col_b = st.columns(2)
        n_brg = col_a.text_input("Nama Barang (Contoh: SUSU, KULIT, DLL)").upper()
        h_brg = col_b.number_input("Harga Satuan Kantor", min_value=0)
        if st.button("Simpan Barang/Harga"):
            if n_brg:
                st.session_state.prices[n_brg] = h_brg
                if n_brg not in st.session_state.stok_gudang:
                    st.session_state.stok_gudang[n_brg] = 0
                save_all(); st.success(f"Barang {n_brg} Berhasil Disimpan!"); st.rerun()
        
        st.write("---")
        st.subheader("Daftar Harga Saat Ini")
        # Tabel Harga dengan tombol hapus
        for k, v in list(st.session_state.prices.items()):
            c_item, c_price, c_del = st.columns([3, 2, 1])
            c_item.write(k)
            c_price.write(f"Rp {v:,}")
            if c_del.button("Hapus", key=f"del_{k}"):
                del st.session_state.prices[k]
                if k in st.session_state.stok_gudang: del st.session_state.stok_gudang[k]
                save_all(); st.rerun()

    with t2:
        st.subheader("Data Member")
        edited_df = st.data_editor(st.session_state.members, use_container_width=True, num_rows="dynamic")
        if st.button("Simpan Perubahan Member"):
            st.session_state.members = edited_df
            save_all(); st.success("Data Member Diperbarui!")