import streamlit as st
import pandas as pd
from datetime import datetime
import os
import requests

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Game Office Pro Manager", layout="wide", page_icon="🏢")

# --- 2. CONFIG DISCORD WEBHOOK ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1468099495618154678/Po4YOGpepU260wlm7Tk5ZGwTYnId-l7zHzYVwgFQklmmKGs363e5y2yw_xrtDlxds7wC"

def send_to_discord(message):
    try:
        data = {"content": message}
        requests.post(DISCORD_WEBHOOK_URL, json=data)
    except Exception as e:
        st.error(f"Gagal kirim ke Discord: {e}")

# --- 3. DAFTAR MEMBER DEFAULT ---
DEFAULT_NAMES = [
    "JOE JETZY", "REXY NUGROHO", "ALEXANDRO JETZY", "VAREL", "NOAH", 
    "JAMAL", "BANGPOK", "KARELA", "HANS", "AMAT LINCOLN", 
    "JOHAN CUKARDELENG", "FRANK CUKARDELENG", "MAX EL STEIN", "BIG BOS", 
    "ARUL", "REY", "CHEONG", "VICKTOR", "MARO", "SUGGEW", "NUSA", "WAHAB", "FRIOREN"
]

# --- 4. FUNGSI DATABASE ---
def save_all():
    st.session_state.members.to_csv('members_data.csv', index=False)
    pd.DataFrame(list(st.session_state.prices.items()), columns=['Item', 'Price']).to_csv('price_data.csv', index=False)
    pd.DataFrame(list(st.session_state.stok_gudang.items()), columns=['Item', 'Stok']).to_csv('stok_gudang.csv', index=False)
    st.session_state.pending_tasks.to_csv('pending_tasks.csv', index=False)
    st.session_state.sales_history.to_csv('sales_history.csv', index=False)
    pd.DataFrame(list(st.session_state.stock_bibit.items()), columns=['Item', 'Qty']).to_csv('stock_data.csv', index=False)

def load_data():
    if os.path.exists('members_data.csv'):
        df = pd.read_csv('members_data.csv')
        for col in ['Total Terima', 'Total Kembali', 'Total Uang']:
            if col not in df.columns: df[col] = 0
        st.session_state.members = df
    else:
        st.session_state.members = pd.DataFrame([{'Nama': n, 'Total Terima': 0, 'Total Kembali': 0, 'Total Uang': 0} for n in DEFAULT_NAMES])

    if os.path.exists('pending_tasks.csv'):
        st.session_state.pending_tasks = pd.read_csv('pending_tasks.csv')
    else:
        st.session_state.pending_tasks = pd.DataFrame(columns=['ID', 'User', 'Tipe', 'Detail', 'Status', 'Waktu', 'TotalNominal', 'SisaBibit'])

    if os.path.exists('sales_history.csv'):
        st.session_state.sales_history = pd.read_csv('sales_history.csv')
    else:
        st.session_state.sales_history = pd.DataFrame(columns=['Waktu', 'Pembeli', 'Item', 'Qty', 'HargaJual', 'Total'])

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

    if os.path.exists('stock_data.csv'):
        df_b = pd.read_csv('stock_data.csv')
        st.session_state.stock_bibit = dict(zip(df_b.Item, df_b.Qty))
    else:
        st.session_state.stock_bibit = {"BIBIT CENGKEH": 1000}

if 'members' not in st.session_state:
    load_data()

# --- 5. SIDEBAR MENU ---
st.sidebar.title("🏢 KANTOR PUSAT")
menu = st.sidebar.selectbox("MENU UTAMA", ["📊 Dashboard", "📝 Input Member", "✅ Approval Admin", "💸 Penjualan Luar", "⚙️ Stock Opname", "💰 Atur Harga & Member"])

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring Kantor & Gudang")
    
    # ROW 1: STOK BIBIT
    st.subheader("🌱 Persediaan Bibit (Gudang Bibit)")
    if st.session_state.stock_bibit:
        cols_b = st.columns(len(st.session_state.stock_bibit))
        for i, (item, qty) in enumerate(st.session_state.stock_bibit.items()):
            cols_b[i].metric(item, f"{qty:,} Pcs", delta_color="normal")
    
    st.write("---")
    
    # ROW 2: STOK HASIL (SIAP JUAL)
    st.subheader("📦 Stok Hasil Produksi (Siap Jual ke NPC)")
    if st.session_state.stok_gudang:
        cols_s = st.columns(4)
        for i, (item, qty) in enumerate(st.session_state.stok_gudang.items()):
            cols_s[i % 4].metric(item, f"{qty:,} Unit")
            
    st.write("---")
    
    # ROW 3: RINGKASAN FINANSIAL
    st.subheader("💰 Ringkasan Finansial")
    c_fin1, c_fin2, c_fin3 = st.columns(3)
    total_hutang = st.session_state.members['Total Uang'].sum()
    total_pemasukan = st.session_state.sales_history['Total'].sum()
    
    c_fin1.metric("Total Hutang ke Member", f"Rp {total_hutang:,}")
    c_fin2.metric("Total Pemasukan Kantor", f"Rp {total_pemasukan:,}")
    c_fin3.metric("Profit Bersih Estimasi", f"Rp {total_pemasukan - total_hutang:,}")

    st.write("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏆 Saldo Member (Top 10)")
        st.dataframe(st.session_state.members.sort_values(by="Total Uang", ascending=False)[['Nama', 'Total Uang']].head(10), use_container_width=True, hide_index=True)
    with c2:
        st.subheader("📜 Riwayat Penjualan Terakhir")
        st.dataframe(st.session_state.sales_history.tail(10), use_container_width=True, hide_index=True)

# --- MENU: FORM INPUT MEMBER ---
elif menu == "📝 Input Member":
    st.title("📝 Form Setoran")
    m_name = st.selectbox("Nama Member", st.session_state.members['Nama'].sort_values())
    t1, t2 = st.tabs(["🍀 Setoran Hasil", "🌱 Ambil Bibit"])
    
    with t1:
        detail_setor = []
        rincian_struk_wa = []
        total_nom = 0
        cols = st.columns(3)
        for i, (item, prc) in enumerate(st.session_state.prices.items()):
            q = cols[i % 3].number_input(f"Jumlah {item}", min_value=0, key=f"s_{item}", step=1)
            if q > 0:
                detail_setor.append(f"{item}:{q}")
                rincian_struk_wa.append(f"{item} : {q}")
                total_nom += (q * prc)
        
        v_kembali = st.number_input("Bibit Sisa Kembali", min_value=0)
        if st.button("Kirim Laporan & Buat Struk"):
            if detail_setor:
                new_t = pd.DataFrame([{'ID': datetime.now().timestamp(), 'User': m_name, 'Tipe': 'SETOR', 'Detail': ",".join(detail_setor), 'TotalNominal': total_nom, 'SisaBibit': v_kembali, 'Status': 'Pending', 'Waktu': datetime.now().strftime("%d/%m %H:%M")}])
                st.session_state.pending_tasks = pd.concat([st.session_state.pending_tasks, new_t], ignore_index=True)
                save_all()
                
                tgl = datetime.now().strftime("%d/%m/%y")
                struk_wa = f"SETORAN {tgl}\n\n{m_name}\n" + "\n".join(rincian_struk_wa) + f"\nTOTAL : {total_nom:,}"
                send_to_discord(f"📩 **LAPORAN BARU DARI {m_name}**\n```\n{struk_wa}\n```")
                st.success("Terkirim!")
                st.code(struk_wa, language="text")
            else: st.warning("Isi barang dulu!")

    with t2:
        bbt = st.selectbox("Pilih Bibit", list(st.session_state.stock_bibit.keys()))
        jml = st.number_input("Jumlah Ambil", min_value=1)
        if st.button("Ajukan Ambil Bibit"):
            new_t = pd.DataFrame([{'ID': datetime.now().timestamp(), 'User': m_name, 'Tipe': 'AMBIL', 'Detail': f"{bbt}:{jml}", 'TotalNominal': 0, 'SisaBibit': 0, 'Status': 'Pending', 'Waktu': datetime.now().strftime("%d/%m %H:%M")}])
            st.session_state.pending_tasks = pd.concat([st.session_state.pending_tasks, new_t], ignore_index=True)
            save_all(); st.success("Permintaan Ambil Bibit terkirim!")

# --- MENU: APPROVAL ---
elif menu == "✅ Approval Admin":
    st.title("✅ Approval Admin")
    pending = st.session_state.pending_tasks[st.session_state.pending_tasks['Status'] == 'Pending']
    if pending.empty: st.info("Tidak ada antrean laporan.")
    else:
        for idx, row in pending.iterrows():
            with st.expander(f"{row['User']} - {row['Tipe']} ({row['Waktu']})"):
                st.write(f"Detail: {row['Detail']}")
                c1, c2 = st.columns(2)
                if c1.button("APPROVE ✅", key=f"ok_{idx}"):
                    midx = st.session_state.members[st.session_state.members['Nama'] == row['User']].index[0]
                    if row['Tipe'] == 'SETOR':
                        for i in row['Detail'].split(","):
                            n, v = i.split(":")
                            st.session_state.stok_gudang[n] = st.session_state.stok_gudang.get(n, 0) + int(v)
                        st.session_state.members.at[midx, 'Total Uang'] += row['TotalNominal']
                        send_to_discord(f"✅ **SETORAN DISETUJUI**\nMember: {row['User']}\nSaldo Bertambah: Rp {row['TotalNominal']:,}")
                    elif row['Tipe'] == 'AMBIL':
                        n, v = row['Detail'].split(":")
                        if st.session_state.stock_bibit[n] >= int(v):
                            st.session_state.stock_bibit[n] -= int(v)
                            st.session_state.members.at[midx, 'Total Terima'] += int(v)
                            send_to_discord(f"🌱 **AMBIL BIBIT DISETUJUI**\nMember: {row['User']}\nItem: {n} sebanyak {v}")
                        else:
                            st.error("Gagal! Stok bibit di gudang tidak cukup.")
                            continue
                    
                    st.session_state.pending_tasks.at[idx, 'Status'] = 'Approved'
                    save_all(); st.rerun()
                
                if c2.button("REJECT ❌", key=f"no_{idx}"):
                    st.session_state.pending_tasks.at[idx, 'Status'] = 'Rejected'
                    save_all(); st.rerun()

# --- MENU: PENJUALAN LUAR ---
elif menu == "💸 Penjualan Luar":
    st.title("💸 Penjualan ke NPC / Pasar")
    with st.form("form_jual"):
        pembeli = st.text_input("Nama Pembeli", value="NPC PASAR")
        item_j = st.selectbox("Pilih Barang dari Gudang", list(st.session_state.stok_gudang.keys()))
        col1, col2 = st.columns(2)
        q_j = col1.number_input("Jumlah Unit yang Dijual", min_value=1)
        h_j = col2.number_input("Harga Jual Satuan (NPC)", min_value=0)
        submit = st.form_submit_button("Konfirmasi Jual")
        
        if submit:
            if st.session_state.stok_gudang.get(item_j, 0) >= q_j:
                st.session_state.stok_gudang[item_j] -= q_j
                total_jual = q_j * h_j
                new_s = pd.DataFrame([{'Waktu': datetime.now().strftime("%d/%m %H:%M"), 'Pembeli': pembeli, 'Item': item_j, 'Qty': q_j, 'HargaJual': h_j, 'Total': total_jual}])
                st.session_state.sales_history = pd.concat([st.session_state.sales_history, new_s], ignore_index=True)
                save_all()
                send_to_discord(f"💸 **PENJUALAN KANTOR**\nBarang: {item_j}\nQty: {q_j}\nTotal Pemasukan: Rp {total_jual:,}")
                st.success(f"Berhasil terjual! Pemasukan: Rp {total_jual:,}")
                st.rerun()
            else:
                st.error("Stok gudang tidak cukup untuk penjualan ini!")

# --- MENU: STOCK OPNAME ---
elif menu == "⚙️ Stock Opname":
    st.title("⚙️ Koreksi Stok (Stock Opname)")
    st.info("Menu ini digunakan untuk menyesuaikan angka stok jika terjadi selisih dengan di Game.")
    
    tab1, tab2 = st.tabs(["📦 Koreksi Stok Barang", "🌱 Koreksi Stok Bibit"])
    
    with tab1:
        st.subheader("Update Stok Barang")
        item_so = st.selectbox("Barang", list(st.session_state.stok_gudang.keys()), key="so1")
        qty_so = st.number_input("Jumlah Fisik Sebenarnya", min_value=0, value=st.session_state.stok_gudang[item_so])
        if st.button("Simpan Perubahan Barang"):
            st.session_state.stok_gudang[item_so] = qty_so
            save_all(); st.success("Stok Barang Berhasil Diupdate!"); st.rerun()
            
    with tab2:
        st.subheader("Update Stok Bibit")
        bibit_so = st.selectbox("Bibit", list(st.session_state.stock_bibit.keys()), key="so2")
        qty_b_so = st.number_input("Jumlah Fisik Sebenarnya", min_value=0, value=st.session_state.stock_bibit[bibit_so])
        if st.button("Simpan Perubahan Bibit"):
            st.session_state.stock_bibit[bibit_so] = qty_b_so
            save_all(); st.success("Stok Bibit Berhasil Diupdate!"); st.rerun()

# --- MENU: PENGATURAN HARGA & MEMBER ---
elif menu == "💰 Atur Harga & Member":
    st.title("⚙️ Pengaturan Dasar")
    t1, t2 = st.tabs(["💰 Daftar Harga Beli Kantor", "👥 Manajemen Member"])
    
    with t1:
        st.subheader("Tambah Jenis Barang Baru")
        col_n, col_h = st.columns(2)
        n_brg = col_n.text_input("Nama Barang (Contoh: DAUN)").upper()
        h_brg = col_h.number_input("Harga Beli dari Member", min_value=0)
        if st.button("Simpan Barang"):
            if n_brg:
                st.session_state.prices[n_brg] = h_brg
                if n_brg not in st.session_state.stok_gudang: st.session_state.stok_gudang[n_brg] = 0
                save_all(); st.success("Barang Baru Terdaftar!"); st.rerun()
        st.write("---")
        st.subheader("Daftar Harga Saat Ini")
        for k, v in list(st.session_state.prices.items()):
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.write(k); c2.write(f"Rp {v:,}")
            if c3.button("Hapus", key=f"del_p_{k}"):
                del st.session_state.prices[k]
                if k in st.session_state.stok_gudang: del st.session_state.stok_gudang[k]
                save_all(); st.rerun()
                
    with t2:
        st.subheader("Tambah Member Baru")
        new_m = st.text_input("Nama Lengkap Member").upper()
        if st.button("Daftarkan Member"):
            if new_m and new_m not in st.session_state.members['Nama'].values:
                new_row = pd.DataFrame([{'Nama': new_m, 'Total Terima': 0, 'Total Kembali': 0, 'Total Uang': 0}])
                st.session_state.members = pd.concat([st.session_state.members, new_row], ignore_index=True)
                save_all(); st.success(f"{new_m} Berhasil Didaftarkan!"); st.rerun()
        
        st.write("---")
        st.subheader("Edit Data Member (Tabel)")
        edited = st.data_editor(st.session_state.members, use_container_width=True, num_rows="dynamic")
        if st.button("Simpan Semua Perubahan Member"):
            st.session_state.members = edited
            save_all(); st.success("Data Member diperbarui!")
