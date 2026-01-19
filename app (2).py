import streamlit as st
import pandas as pd
from datetime import date, time, datetime, timedelta
from io import BytesIO
import sqlite3
import uuid
import bcrypt
import json

# CONFIG
st.set_page_config(
    page_title="Sistem Kursus UKL",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# DATABASE
conn = sqlite3.connect("ukl.db", check_same_thread=False)
c = conn.cursor()

# TABLES
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password BLOB
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,
    nama TEXT,
    tempat TEXT,
    tarikh TEXT,
    masa_mula TEXT,
    masa_tamat TEXT
)
""")
conn.commit()

# MIGRATION DATABASE LAMA
try:
    c.execute("ALTER TABLE courses ADD COLUMN tarikh_mula TEXT")
except sqlite3.OperationalError:
    pass
try:
    c.execute("ALTER TABLE courses ADD COLUMN tarikh_tamat TEXT")
except sqlite3.OperationalError:
    pass
try:
    c.execute("ALTER TABLE courses ADD COLUMN tempat TEXT")
except sqlite3.OperationalError:
    pass
try:
    c.execute("ALTER TABLE courses ADD COLUMN jadual TEXT")
except sqlite3.OperationalError:
    pass

conn.commit()

# Convert data lama ke format baru
c.execute("SELECT id, tarikh, masa_mula, masa_tamat, tempat, jadual FROM courses")
rows = c.fetchall()

for kursus_id, tarikh, mula, tamat, _, jadual_existing in rows:
    if not all([tarikh, mula, tamat]):
        continue

    # SKIP kalau sudah migrate
    if jadual_existing:
        continue

    jadual = {
        pd.to_datetime(tarikh).date().isoformat(): {
            "mula": mula,
            "tamat": tamat
        }
    }

    c.execute("""
        UPDATE courses 
        SET tarikh_mula=?, tarikh_tamat=?, jadual=?
        WHERE id=?
    """, (tarikh, tarikh, json.dumps(jadual), kursus_id))

conn.commit()

# DEFAULT USER
c.execute("SELECT COUNT(*) FROM users WHERE username='uklkedah'")
if c.fetchone()[0] == 0:
    hashed = bcrypt.hashpw("Uklkedah@1234".encode(), bcrypt.gensalt())
    c.execute(
        "INSERT INTO users (username, password) VALUES (?,?)",
        ("uklkedah", hashed)
    )
    conn.commit()

# LOAD DATA
def load_data():
    df = pd.read_sql("SELECT * FROM courses", conn)
    if df.empty:
        return df

    df["tarikh_mula"] = pd.to_datetime(df["tarikh_mula"], errors='coerce').dt.date
    df["tarikh_tamat"] = pd.to_datetime(df["tarikh_tamat"], errors='coerce').dt.date
    return df

# LOGIN STATE
if "login" not in st.session_state:
    st.session_state.login = False

# LOGIN PAGE
if not st.session_state.login:
    st.markdown("""
    <style>
    .login-box {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 8px;
        box-shadow: 0 0 8px rgba(0,0,0,0.08);
        max-width: 380px;
        margin: auto;
    }
    .login-title {
        text-align: center;
        font-weight: 600;
        margin-bottom: 5px;
    }
    .login-subtitle {
        text-align: center;
        font-size: 14px;
        color: #555;
        margin-bottom: 20px;
    }
    .footer {
        text-align: center;
        font-size: 12px;
        color: #777;
        margin-top: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

    # CENTER PAGE
    sp1, sp2, sp3 = st.columns([1, 2, 1])

    # LOGO CENTER
    lc1, lc2, lc3 = st.columns([2, 1.5, 2])

    with lc2:
        st.image("logo_kastam.svg")

        # TITLE
        st.markdown("""
        <div class="login-title">JABATAN KASTAM DIRAJA MALAYSIA</div>
        <div class="login-subtitle">Unit Korporat & Latihan (UKL)</div>
        """, unsafe_allow_html=True)

        # LOGIN BOX
        st.markdown('<div class="login-box">', unsafe_allow_html=True)

        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("LOGIN", use_container_width=True):
            c.execute(
                "SELECT password FROM users WHERE username=?",
                (u.strip(),)
            )
            row = c.fetchone()

            if row and bcrypt.checkpw(p.encode(), row[0]):
                st.session_state.login = True
                st.rerun()
            else:
                st.error("Username atau password tidak sah")

        st.markdown('</div>', unsafe_allow_html=True)

        # FOOTER
        st.markdown("""
        <div class="footer">
        © Jabatan Kastam Diraja Malaysia
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# 🔔 NOTIFICATION
df = load_data()
now = datetime.now()

if not df.empty:
    for _, r in df.iterrows():
        if not r["jadual"]:
            continue

        jadual = json.loads(r["jadual"])

        for tarikh, masa in jadual.items():
            start = datetime.combine(
                date.fromisoformat(tarikh),
                datetime.strptime(masa["mula"], "%H:%M").time()
            )
            end = datetime.combine(
                date.fromisoformat(tarikh),
                datetime.strptime(masa["tamat"], "%H:%M").time()
            )

            if now < start <= now + timedelta(minutes=30):
                st.toast(f"{r['nama']} bermula jam {masa['mula']}", icon="📢")

            if start <= now <= end:
                st.toast(f"{r['nama']} sedang berlangsung", icon="🔴")

# SIDEBAR
with st.sidebar:  
    st.image("logo_kastam.svg", width=80)
    menu = st.radio(
        "Menu Sistem",
        [
            "Muka Hadapan",
            "Key-In Kursus",
            "Dashboard Kursus",
            "Whiteboard Digital",
            "Export Data"
        ]
    )
    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state.login = False
        st.rerun()

# HEADER
st.title("Sistem Pengurusan Kursus UKL")
st.caption("Jabatan Kastam Diraja Malaysia – Kedah")

# MUKA HADAPAN
if menu == "Muka Hadapan":
    st.info("Selamat Datang ke Unit Korporat & Latihan (UKL)")
    st.markdown("""
    **Unit Korporat & Latihan (UKL)** merupakan unit di bawah  
    **Bahagian Khidmat Pengurusan & Sumber Manusia (KPSM)** yang bertanggungjawab ke atas hal ehwal perkhidmatan dan latihan kakitangan JKDM termasuk penyelenggaraan serta pengemaskinian data perjawatan pegawai, di samping memproses permohonan perintah penempatan dan pertukaran pegawai. Skop tanggungjawab ini turut merangkumi aspek pengambilan, pengesahan dalam jawatan, kenaikan pangkat dan pemangkuan serta kemasukan ke dalam jawatan berpencen bagi anggota JKDM dan gunasama. Selain itu, fungsi ini berperanan menyusun semula dan memperkukuhkan organisasi melalui penyediaan perkhidmatan yang cepat, cekap, adil dan berkesan selaras dengan perkembangan ekonomi semasa, di samping mengubal dasar pengurusan sumber manusia dan skim-skim perkhidmatan di JKDM. Peranan ini juga melibatkan penggubalan dan pengurusan dasar latihan anggota berdasarkan keperluan latihan (training needs) serta pembangunan kemajuan kerjaya anggota JKDM dan gunasama, seterusnya memastikan penggunaan sumber manusia secara optimum melalui sistem penyampaian yang berkesan dan cekap berpandukan dasar latihan, pelan strategik dan konsep yang menyokong pencapaian objektif organisasi.
    """)


# KEY-IN KURSUS
elif menu == "Key-In Kursus":
    import json
    from datetime import timedelta

    # INIT SESSION STATE
    if "jadual" not in st.session_state:
        st.session_state.jadual = {}

    if "hari_index" not in st.session_state:
        st.session_state.hari_index = 0

    with st.form("kursus"):
        nama = st.text_input("Nama Kursus")
        tempat = st.text_input("Tempat")

        col1, col2 = st.columns(2)
        tarikh_mula = col1.date_input("Tarikh Mula", date.today())
        tarikh_tamat = col2.date_input("Tarikh Tamat", date.today())

        # Jana senarai tarikh
        senarai_tarikh = []
        current = tarikh_mula
        while current <= tarikh_tamat:
            senarai_tarikh.append(current)
            current += timedelta(days=1)

        st.markdown("### Masa")

        # Hadkan index supaya tak lebih tarikh
        if st.session_state.hari_index < len(senarai_tarikh):
            tarikh = senarai_tarikh[st.session_state.hari_index]

            st.markdown(f"**{tarikh.strftime('%d/%m/%Y')}**")
            m1, m2 = st.columns(2)

            mula = m1.time_input(
                "Masa Mula",
                time(9, 0),
                key=f"mula_{tarikh}"
            )
            tamat = m2.time_input(
                "Masa Tamat",
                time(17, 0),
                key=f"tamat_{tarikh}"
            )

        colA, colB = st.columns(2)

        tambah = colA.form_submit_button("Tambah Hari")
        simpan = colB.form_submit_button("Simpan Kursus")

        # BUTTON TAMBAH HARI
        if tambah and st.session_state.hari_index < len(senarai_tarikh):
            st.session_state.jadual[tarikh.isoformat()] = {
                "mula": mula.strftime("%H:%M"),
                "tamat": tamat.strftime("%H:%M")
            }
            st.session_state.hari_index += 1

        # BUTTON SIMPAN
        if simpan:
            c.execute(
                """
                INSERT INTO courses (id, nama, tarikh_mula, tarikh_tamat, tempat, jadual)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    str(uuid.uuid4()),
                    nama,
                    tarikh_mula.isoformat(),
                    tarikh_tamat.isoformat(),
                    tempat,
                    json.dumps(st.session_state.jadual)
                )
            )
            conn.commit()

            # RESET
            st.session_state.jadual = {}
            st.session_state.hari_index = 0

            st.success("Kursus berjaya disimpan!")

# DASHBOARD
elif menu == "Dashboard Kursus":

    st.markdown("## Dashboard Kursus")
    st.markdown(
        "Paparan senarai kursus dan program latihan bagi tujuan pemantauan "
        "serta rujukan pengurusan."
    )

    st.divider()

    df = load_data()

    if df.empty:
        st.info("Tiada rekod kursus atau program direkodkan setakat ini.")
    else:
        # FORMAT TARIKH
        df["Tarikh Mula"] = pd.to_datetime(df["tarikh_mula"])
        df["Tarikh Tamat"] = pd.to_datetime(df["tarikh_tamat"])

        # EKSTRAK MASA DARI JADUAL
        def extract_masa(jadual_json):
            try:
                jadual = json.loads(jadual_json)
                first_day = list(jadual.values())[0]
                return f"{first_day['mula']} - {first_day['tamat']}"
            except:
                return "-"

        df["Masa"] = df["jadual"].apply(extract_masa)

           # PILIH & NAMA SEMULA COLUMN
        paparan = df.rename(columns={
            "nama": "Nama Program",
            "tempat": "Tempat"
        })[
            ["Nama Program", "Tempat", "Tarikh Mula", "Tarikh Tamat", "Masa"]
        ]

        # PAPAR JADUAL
       
        st.dataframe(
            paparan,
            use_container_width=True,
            hide_index=True
        )

# WHITEBOARD DIGITAL
elif menu == "Whiteboard Digital":
    df = load_data()
    now = datetime.now()
    ada = False

    for _, r in df.iterrows():
        jadual = json.loads(r["jadual"])

        for tarikh, masa in jadual.items():
            mula = datetime.combine(
                date.fromisoformat(tarikh),
                datetime.strptime(masa["mula"], "%H:%M").time()
            )
            tamat = datetime.combine(
                date.fromisoformat(tarikh),
                datetime.strptime(masa["tamat"], "%H:%M").time()
            )

            if mula <= now <= tamat:
                ada = True
                st.error(f"🔴 {r['nama']} sedang berlangsung\n📍 {r['tempat']}")

            elif now < mula:
                ada = True
                st.info(f"⏳ {r['nama']} akan bermula {tarikh} {masa['mula']}")

    if not ada:
        st.success("Tiada kursus aktif")

# EXPORT
elif menu == "Export Data":
    df = load_data()
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.drop(columns=["id"], errors="ignore").to_excel(writer, index=False)

    st.download_button(
        "Download Excel",
        buffer.getvalue(),
        "kursus_ukl.xlsx"
    )