import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import requests

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Game Office Pro Manager", layout="wide", page_icon="🏢")

# --- 2. CONFIG DISCORD WEBHOOK (AMAN) ---
try:
    DISCORD_WEBHOOK_URL = st.secrets["MY_WEBHOOK_URL"]
except:
    st.error("⚠️ Webhook belum dikonfigurasi di Streamlit Secrets!")
    DISCORD_WEBHOOK_URL = None

def send_to_discord(message):
    if DISCORD_WEBHOOK_URL:
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
        df_tasks = pd.read_csv('pending_tasks.csv')
        if 'FullTimestamp' not in df_tasks.columns:
            df_tasks['FullTimestamp'] = datetime.now()
        st.session_state.pending_tasks = df_tasks
    else:
        st.session_state.pending_tasks = pd.DataFrame(columns=['ID', 'User', 'Tipe', 'Detail', 'Status', 'Waktu', 'TotalNominal', 'SisaBibit', 'FullTimestamp'])

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

st.sidebar.write("---")
range_view = st.sidebar.radio("Range Waktu Leaderboard:", ["Semua", "Hari Ini", "7 Hari Terakhir"])

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Monitoring Dashboard")
    
    df_approved = st.session_state.pending_tasks[st.session_state.pending_tasks['Status'] == 'Approved'].copy()
    df_approved['FullTimestamp'] = pd.to_datetime(df_approved['FullTimestamp'])
    
    if range_view == "Hari Ini":
        df_approved = df_approved[df_approved['FullTimestamp'].dt.date == datetime.now().date()]
    elif range_view == "7 Hari Terakhir":
        limit_date = datetime.now() - timedelta(days=7)
        df_approved = df_approved[df_approved['FullTimestamp'] >= limit_date]

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🌱 Stok Bibit")
        cols_b = st.columns(len(st.session_state.stock_bibit))
        for i, (item, qty) in enumerate(st.session_state.stock_bibit.items()):
            cols_b[i].metric(item, f"{qty:,} Pcs")
    with c2:
        st.subheader("📦 Stok Gudang")
        items = list(st.session_state.stok_gudang.items())
        cols_s = st.columns(max(1, len(items)))
        for i, (item, qty) in enumerate(items):
            cols_s[i].metric(item, f"{qty:,}")

    st.write("---")
    st.subheader(f"🏆 Leaderboard Member ({range_view})")
    l1, l2 = st.columns(2)
    
    with l1:
        st.markdown("### ⭐ Penyetor Terbanyak (Rp)")
        if not df_approved[df_approved['Tipe'] == 'SETOR'].empty:
            top_setor = df_approved[df_approved['Tipe'] == 'SETOR'].groupby('User')['TotalNominal'].sum().reset_index()
            top_setor = top_setor.sort_values(by='TotalNominal', ascending=False)
            st.dataframe(top_setor.rename(columns={'TotalNominal': 'Total Setoran (Rp)'}), use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada data setoran.")

    with l2:
        st.markdown("### 🌱 Pengambil Bibit Terbanyak")
        if not df_approved[df_approved['Tipe'] == 'AMBIL'].empty:
            df_ambil = df_approved[df_approved['Tipe'] == 'AMBIL'].copy()
            df_ambil['QtyAmbil'] = df_ambil['Detail'].apply(lambda x: int(x.split(':')[1]) if ':' in x else 0)
            top_ambil = df_ambil.groupby('User')['QtyAmbil'].sum().reset_index()
            top_ambil = top_ambil.sort_values(by='QtyAmbil', ascending=False)
            st.dataframe(top_ambil.rename(columns={'QtyAmbil': 'Total Bibit (Pcs)'}), use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada data pengambilan bibit.")

# --- MENU: INPUT MEMBER ---
elif menu == "📝 Input Member":
    st.title("📝 Form Input Member")
    m_name = st.selectbox("Pilih Member", st.session_state.members['Nama'].sort_values())
    t1, t2 = st.tabs(["🍀 Setoran Hasil", "🌱 Ambil Bibit"])
    
    with t1:
        cols = st.columns(3)
        detail_setor, rincian_struk, total_nom = [], [], 0
        for i, (item, prc) in enumerate(st.session_state.prices.items()):
            q = cols[i % 3].number_input(f"Jumlah {item}", min_value=0, key=f"inp_{item}", step=1)
            if q > 0:
                detail_setor.append(f"{item}:{q}")
                rincian_struk.append(f"{item} : {q:,}")
                total_nom += (q * prc)
        
        sisa_b = st.number_input("Bibit Sisa yang Dikembalikan", min_value=0)
        if st.button("Kirim Laporan Setoran"):
            if detail_setor:
                new_t = pd.DataFrame([{'ID': datetime.now().timestamp(), 'User': m_name, 'Tipe': 'SETOR', 'Detail': ",".join(detail_setor), 'TotalNominal': total_nom, 'SisaBibit': sisa_b, 'Status': 'Pending', 'Waktu': datetime.now().strftime("%d/%m %H:%M"), 'FullTimestamp': datetime.now()}])
                st.session_state.pending_tasks = pd.concat([st.session_state.pending_tasks, new_t], ignore_index=True)
                save_all()
                
                # FORMAT PESAN SESUAI PERMINTAAN
                tgl = datetime.now().strftime("%d/%m/%y")
                pesan_discord = f"**SETORAN {tgl}**\n\n"
                pesan_discord += f"**{m_name}**\n"
                pesan_discord += "\n".join(rincian_struk) + "\n"
                pesan_discord += f"**TOTAL : {total_nom:,}**"
                
                send_to_discord(pesan_discord)
                st.success("Laporan terkirim!")
                st.code(pesan_discord, language="text")
            else: st.warning("Input barang dulu!")

    with t2:
        bbt = st.selectbox("Pilih Bibit", list(st.session_state.stock_bibit.keys()))
        jml = st.number_input("Jumlah Ambil", min_value=1, step=1)
        if st.button("Ajukan Ambil Bibit"):
            new_t = pd.DataFrame([{'ID': datetime.now().timestamp(), 'User': m_name, 'Tipe': 'AMBIL', 'Detail': f"{bbt}:{jml}", 'TotalNominal': 0, 'SisaBibit': 0, 'Status': 'Pending', 'Waktu': datetime.now().strftime("%d/%m %H:%M"), 'FullTimestamp': datetime.now()}])
            st.session_state.pending_tasks = pd.concat([st.session_state.pending_tasks, new_t], ignore_index=True)
            save_all(); st.success("Permintaan Ambil Bibit terkirim!")

# --- MENU: APPROVAL & BAYAR ---
elif menu == "✅ Approval & Bayar":
    st.title("✅ Persetujuan & Pembayaran")
    pending = st.session_state.pending_tasks[st.session_state.pending_tasks['Status'] == 'Pending']
    
    if pending.empty:
        st.info("Tidak ada laporan baru.")
    else:
        for idx, row in pending.iterrows():
            with st.expander(f"{row['User']} - {row['Tipe']} ({row['Waktu']})"):
                st.write(f"Detail: {row['Detail']}")
                if st.button("BAYAR / KONFIRMASI ✅", key=f"app_{idx}"):
                    midx = st.session_state.members[st.session_state.members['Nama'] == row['User']].index[0]
                    if row['Tipe'] == 'SETOR':
                        for item_data in row['Detail'].split(","):
                            n_i, q_i = item_data.split(":")
                            st.session_state.stok_gudang[n_i] = st.session_state.stok_gudang.get(n_i, 0) + int(q_i)
                        st.session_state.members.at[midx, 'Total Uang'] += row['TotalNominal']
                        
                        pesan_bayar = f"✅ **SUDAH DIBAYAR**\nKepada : **{row['User']}**\nSebanyak : **Rp {row['TotalNominal']:,}**"
                        send_to_discord(pesan_bayar)
                    elif row['Tipe'] == 'AMBIL':
                        n_b, q_b = row['Detail'].split(":")
                        st.session_state.stock_bibit[n_b] -= int(q_b)
                        st.session_state.members.at[midx, 'Total Terima'] += int(q_b)
                        send_to_discord(f"🌱 **BIBIT DIAMBIL:** {row['User']} mengambil {q_b} pcs {n_b}")
                    
                    st.session_state.pending_tasks.at[idx, 'Status'] = 'Approved'
                    save_all(); st.rerun()

# --- MENU LAINNYA ---
elif menu == "💸 Penjualan Luar":
    st.title("💸 Jual ke NPC")
    with st.form("jual_npc"):
        item_j = st.selectbox("Barang", list(st.session_state.stok_gudang.keys()))
        qty_j = st.number_input("Jumlah", min_value=1)
        prc_j = st.number_input("Harga Satuan", min_value=0)
        if st.form_submit_button("Jual"):
            if st.session_state.stok_gudang[item_j] >= qty_j:
                st.session_state.stok_gudang[item_j] -= qty_j
                total = qty_j * prc_j
                new_s = pd.DataFrame([{'Waktu': datetime.now().strftime("%d/%m %H:%M"), 'Pembeli': 'NPC', 'Item': item_j, 'Qty': qty_j, 'HargaJual': prc_j, 'Total': total}])
                st.session_state.sales_history = pd.concat([st.session_state.sales_history, new_s], ignore_index=True)
                save_all(); st.success("Terjual!"); st.rerun()

elif menu == "⚙️ Stock Opname":
    st.title("⚙️ Koreksi Stok")
    tab1, tab2 = st.tabs(["📦 Stok Barang", "🌱 Stok Bibit"])
    with tab1:
        if st.session_state.stok_gudang:
            i_so = st.selectbox("Pilih Barang", list(st.session_state.stok_gudang.keys()), key="so_brg")
            q_so = st.number_input("Jumlah Sebenarnya", value=st.session_state.stok_gudang[i_so], key="so_brg_val")
            if st.button("Update Stok Barang"):
                st.session_state.stok_gudang[i_so] = q_so
                save_all(); st.rerun()
    with tab2:
        if st.session_state.stock_bibit:
            b_so = st.selectbox("Pilih Bibit", list(st.session_state.stock_bibit.keys()), key="so_bbt")
            qb_so = st.number_input("Jumlah Sebenarnya", value=st.session_state.stock_bibit[b_so], key="so_bbt_val")
            if st.button("Update Stok Bibit"):
                st.session_state.stock_bibit[b_so] = qb_so
                save_all(); st.rerun()

elif menu == "💰 Atur Harga & Member":
    st.title("⚙️ Pengaturan")
    t1, t2 = st.tabs(["Harga", "Member"])
    with t1:
        n_b = st.text_input("Nama Barang Baru").upper()
        h_b = st.number_input("Harga", min_value=0)
        if st.button("Tambah"):
            st.session_state.prices[n_b] = h_b
            st.session_state.stok_gudang[n_b] = 0
            save_all(); st.rerun()
    with t2:
        edited = st.data_editor(st.session_state.members, use_container_width=True, num_rows="dynamic")
        if st.button("Simpan Member"):
            st.session_state.members = edited; save_all(); st.success("Tersimpan!")
