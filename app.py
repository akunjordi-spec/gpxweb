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
        pass

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
        st.session_state.members = pd.read_csv('members_data.csv')
    else:
        st.session_state.members = pd.DataFrame([{'Nama': n, 'Total Terima': 0, 'Total Kembali': 0, 'Total Uang': 0} for n in DEFAULT_NAMES])
    
    for col in ['Total Terima', 'Total Kembali', 'Total Uang']:
        if col not in st.session_state.members.columns:
            st.session_state.members[col] = 0

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

# --- 5. SIDEBAR ---
st.sidebar.title("🏢 KANTOR PUSAT")
menu = st.sidebar.selectbox("MENU UTAMA", ["📊 Dashboard", "📝 Input Member", "✅ Approval & Bayar", "💸 Penjualan Luar", "⚙️ Stock Opname", "💰 Atur Harga & Member"])

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring Dashboard")
    
    st.subheader("🌱 Stok Bibit")
    cols_b = st.columns(len(st.session_state.stock_bibit))
    for i, (item, qty) in enumerate(st.session_state.stock_bibit.items()):
        cols_b[i].metric(item, f"{qty:,} Pcs")
    
    st.subheader("📦 Stok Gudang Kantor (Siap Jual)")
    cols_s = st.columns(4)
    for i, (item, qty) in enumerate(st.session_state.stok_gudang.items()):
        cols_s[i % 4].metric(item, f"{qty:,} Unit")

    st.write("---")
    c_f1, c_f2 = st.columns(2)
    c_f1.metric("Total Pembayaran ke Member", f"Rp {st.session_state.members['Total Uang'].sum():,}")
    c_f2.metric("Total Penjualan NPC", f"Rp {st.session_state.sales_history['Total'].sum():,}")

# --- MENU: INPUT MEMBER ---
elif menu == "📝 Input Member":
    st.title("📝 Form Input Member")
    m_name = st.selectbox("Pilih Member", st.session_state.members['Nama'].sort_values())
    t1, t2 = st.tabs(["🍀 Setoran Hasil", "🌱 Ambil Bibit"])
    
    with t1:
        st.info("💡 Klik tombol ini untuk mengirim rincian setoran ke Admin.")
        cols = st.columns(3)
        detail_setor, rincian_struk, total_nom = [], [], 0
        for i, (item, prc) in enumerate(st.session_state.prices.items()):
            q = cols[i % 3].number_input(f"Jumlah {item}", min_value=0, key=f"inp_{item}", step=1)
            if q > 0:
                detail_setor.append(f"{item}:{q}")
                rincian_struk.append(f"{item}: {q}")
                total_nom += (q * prc)
        
        sisa_b = st.number_input("Bibit Sisa yang Dikembalikan", min_value=0)
        if st.button("Kirim Laporan Setoran"):
            if detail_setor:
                new_t = pd.DataFrame([{'ID': datetime.now().timestamp(), 'User': m_name, 'Tipe': 'SETOR', 'Detail': ",".join(detail_setor), 'TotalNominal': total_nom, 'SisaBibit': sisa_b, 'Status': 'Pending', 'Waktu': datetime.now().strftime("%d/%m %H:%M")}])
                st.session_state.pending_tasks = pd.concat([st.session_state.pending_tasks, new_t], ignore_index=True)
                save_all()
                
                tgl = datetime.now().strftime("%d/%m/%y")
                struk_txt = f"SETORAN {tgl}\n\n{m_name}\n" + "\n".join(rincian_struk) + f"\nTOTAL : {total_nom:,}"
                send_to_discord(f"📩 **LAPORAN SETORAN BARU**\n```\n{struk_txt}\n```")
                
                st.success("Laporan terkirim!")
                st.code(struk_txt, language="text")
            else: st.warning("Input jumlah barang dulu!")

    with t2:
        bbt = st.selectbox("Pilih Bibit", list(st.session_state.stock_bibit.keys()))
        jml = st.number_input("Jumlah Ambil", min_value=1, step=1)
        if st.button("Ajukan Ambil Bibit"):
            new_t = pd.DataFrame([{'ID': datetime.now().timestamp(), 'User': m_name, 'Tipe': 'AMBIL', 'Detail': f"{bbt}:{jml}", 'TotalNominal': 0, 'SisaBibit': 0, 'Status': 'Pending', 'Waktu': datetime.now().strftime("%d/%m %H:%M")}])
            st.session_state.pending_tasks = pd.concat([st.session_state.pending_tasks, new_t], ignore_index=True)
            save_all(); st.success("Permintaan Ambil Bibit terkirim!")

# --- MENU: APPROVAL & BAYAR (LOGIKA BARU) ---
elif menu == "✅ Approval & Bayar":
    st.title("✅ Persetujuan & Pembayaran")
    pending = st.session_state.pending_tasks[st.session_state.pending_tasks['Status'] == 'Pending']
    
    if pending.empty:
        st.info("Tidak ada laporan yang menunggu pembayaran.")
    else:
        for idx, row in pending.iterrows():
            with st.expander(f"{row['User']} - {row['Tipe']} ({row['Waktu']})"):
                st.write(f"**Rincian Barang:** {row['Detail']}")
                st.write(f"**Total yang harus dibayar:** Rp {row['TotalNominal']:,}")
                
                c1, c2 = st.columns(2)
                if c1.button("BAYAR SEKARANG ✅", key=f"app_{idx}"):
                    midx = st.session_state.members[st.session_state.members['Nama'] == row['User']].index[0]
                    
                    if row['Tipe'] == 'SETOR':
                        # Tambah Stok Gudang
                        for item_data in row['Detail'].split(","):
                            nama_item, qty_item = item_data.split(":")
                            st.session_state.stok_gudang[nama_item] = st.session_state.stok_gudang.get(nama_item, 0) + int(qty_item)
                        
                        # Update Saldo Member
                        st.session_state.members.at[midx, 'Total Uang'] += row['TotalNominal']
                        st.session_state.members.at[midx, 'Total Kembali'] += row['SisaBibit']
                        
                        # NOTIFIKASI DISCORD SESUAI PERMINTAAN
                        pesan_bayar = f"✅ **PEMBAYARAN SELESAI**\n"
                        pesan_bayar += f"Sudah dibayar kepada : **{row['User']}**\n"
                        pesan_bayar += f"Setoran sebanyak : **Rp {row['TotalNominal']:,}**\n"
                        pesan_bayar += f"Status : **Terbayarkan**"
                        send_to_discord(pesan_bayar)
                        
                    elif row['Tipe'] == 'AMBIL':
                        nama_bbt, qty_bbt = row['Detail'].split(":")
                        if st.session_state.stock_bibit[nama_bbt] >= int(qty_bbt):
                            st.session_state.stock_bibit[nama_bbt] -= int(qty_bbt)
                            st.session_state.members.at[midx, 'Total Terima'] += int(qty_bbt)
                            send_to_discord(f"🌱 **PENGAMBILAN BIBIT:** {row['User']} sudah menerima {nama_bbt} {qty_bbt} pcs.")
                        else:
                            st.error("Stok Bibit tidak cukup!")
                            continue
                    
                    st.session_state.pending_tasks.at[idx, 'Status'] = 'Approved'
                    save_all(); st.rerun()
                
                if c2.button("TOLAK ❌", key=f"rej_{idx}"):
                    st.session_state.pending_tasks.at[idx, 'Status'] = 'Rejected'
                    save_all(); st.rerun()

# --- MENU PENJUALAN ---
elif menu == "💸 Penjualan Luar":
    st.title("💸 Jual Hasil Gudang ke NPC")
    with st.form("jual_npc"):
        item_j = st.selectbox("Pilih Barang", list(st.session_state.stok_gudang.keys()))
        qty_j = st.number_input("Jumlah Unit", min_value=1)
        prc_j = st.number_input("Harga Jual Satuan", min_value=0)
        if st.form_submit_button("Konfirmasi Penjualan"):
            if st.session_state.stok_gudang[item_j] >= qty_j:
                st.session_state.stok_gudang[item_j] -= qty_j
                total = qty_j * prc_j
                new_s = pd.DataFrame([{'Waktu': datetime.now().strftime("%d/%m %H:%M"), 'Pembeli': 'NPC', 'Item': item_j, 'Qty': qty_j, 'HargaJual': prc_j, 'Total': total}])
                st.session_state.sales_history = pd.concat([st.session_state.sales_history, new_s], ignore_index=True)
                save_all(); 
                send_to_discord(f"💸 **PENJUALAN NPC:** Kantor menjual {qty_j} {item_j} seharga Rp {total:,}")
                st.success("Data penjualan tersimpan!"); st.rerun()
            else: st.error("Stok di gudang tidak cukup!")

# --- MENU STOCK OPNAME ---
elif menu == "⚙️ Stock Opname":
    st.title("⚙️ Koreksi Stok Manual")
    tab1, tab2 = st.tabs(["📦 Stok Barang", "🌱 Stok Bibit"])
    with tab1:
        i_so = st.selectbox("Pilih Barang", list(st.session_state.stok_gudang.keys()), key="so_brg")
        q_so = st.number_input("Jumlah Sebenarnya", value=st.session_state.stok_gudang[i_so], key="so_brg_val")
        if st.button("Update Stok Barang", key="btn_so1"):
            st.session_state.stok_gudang[i_so] = q_so
            save_all(); st.success("Update Berhasil!"); st.rerun()
    with tab2:
        b_so = st.selectbox("Pilih Bibit", list(st.session_state.stock_bibit.keys()), key="so_bbt")
        qb_so = st.number_input("Jumlah Sebenarnya", value=st.session_state.stock_bibit[b_so], key="so_bbt_val")
        if st.button("Update Stok Bibit", key="btn_so2"):
            st.session_state.stock_bibit[b_so] = qb_so
            save_all(); st.success("Update Berhasil!"); st.rerun()

# --- MENU PENGATURAN ---
elif menu == "💰 Atur Harga & Member":
    st.title("⚙️ Pengaturan Dasar")
    t1, t2 = st.tabs(["Daftar Harga Beli Kantor", "Manajemen Nama Member"])
    with t1:
        n_b = st.text_input("Nama Barang Baru").upper()
        h_b = st.number_input("Harga Beli dari Member", min_value=0)
        if st.button("Daftarkan Barang"):
            st.session_state.prices[n_b] = h_b
            if n_b not in st.session_state.stok_gudang: st.session_state.stok_gudang[n_b] = 0
            save_all(); st.success("Barang Terdaftar!"); st.rerun()
    with t2:
        st.write("Gunakan tabel ini untuk menambah/hapus member atau mengedit saldo manual:")
        edited = st.data_editor(st.session_state.members, use_container_width=True, num_rows="dynamic")
        if st.button("Simpan Seluruh Data Member"):
            st.session_state.members = edited
            save_all(); st.success("Data member terbaru disimpan!"); st.rerun()
