from datetime import date, datetime
import hashlib
import hmac
import json
from io import BytesIO
import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Monitoring Kehamilan Kamboja 2B",
    page_icon=":material/favorite:",
    layout="wide",
    initial_sidebar_state="auto",
)

APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "dataset_ibu_hamil_kamboja2b.csv"
EVAL_FILE = APP_DIR / "evaluasi_kader.csv"
RISK_ORDER = ["KRR", "KRT", "KRST", "Perlu verifikasi"]
ADDITIONAL_RISK_COLUMNS = [
    "riwayat_keguguran",
    "kehamilan_kembar",
    "riwayat_hamil_anggur",
    "anemia_berat",
    "penyakit_kronis",
    "kelainan_letak_janin",
    "perdarahan_kehamilan",
    "preeklamsia_berat",
]
SOURCE_COLUMNS = [
    "id_ibu",
    "nama_ibu",
    "nik",
    "nama_suami",
    "usia",
    "tempat_lahir",
    "tanggal_lahir",
    "hpl",
    "usia_hamil",
    "alamat",
    "alergi",
    "riwayat_sakit",
    "tinggi_badan_cm",
    "jarak_kehamilan_tahun",
    "jumlah_anak_hidup",
    "riwayat_caesar",
    "tekanan_darah_sistol",
    "tekanan_darah_diastol",
    "skor_poedji_rochjati",
    "kategori_risiko",
] + ADDITIONAL_RISK_COLUMNS

# --- BANK SOAL EVALUASI KADER ---
EVALUATION_QUESTIONS = [
    {
        "no": 1,
        "question": "Apa kelemahan utama dari sistem pencatatan data kehamilan konvensional (menggunakan buku register kertas dan rekapitulasi manual)?",
        "options": {
            "A": "Proses penginputan data menjadi terlalu instan dan cepat.",
            "B": "Rentan terhadap risiko kehilangan data, kerusakan fisik, duplikasi, dan menyulitkan pelacakan tren riwayat kesehatan.",
            "C": "Membutuhkan spesifikasi komputer/server yang sangat tinggi di lokasi Posyandu.",
            "D": "Data otomatis terhubung langsung ke Rumah Sakit pusat."
        },
        "answer": "B"
    },
    {
        "no": 2,
        "question": "Merujuk pada metode skrining Kartu Skor Poedji Rochjati (KSPR), kehamilan dikategorikan sebagai Kehamilan Risiko Tinggi (KRT) apabila akumulasi skornya berada pada rentang...",
        "options": {
            "A": "Skor total = 2",
            "B": "Skor total = 3 sampai 5",
            "C": "Skor rentang 6 hingga 10",
            "D": "Skor total >= 12"
        },
        "answer": "C"
    },
    {
        "no": 3,
        "question": "Apa fungsi utama dari fitur Early Warning System (Alerts Warning) pada Dashboard Monitoring Kehamilan berbasis web yang dirancang?",
        "options": {
            "A": "Mengirimkan pesan pengingat belanja bulanan untuk ibu hamil.",
            "B": "Mendiagnosis penyakit kronis secara mandiri tanpa bantuan bidan.",
            "C": "Mendeteksi secara cepat adanya anomali klinis (seperti lonjakan tekanan darah) dan menampilkan indikator warna risiko otomatis.",
            "D": "Menghitung biaya persalinan secara otomatis di Rumah Sakit."
        },
        "answer": "C"
    },
    {
        "no": 4,
        "question": "Informasi apa yang dapat dipantau melalui Dashboard Monitoring Kehamilan?",
        "options": {
            "A": "Kategori risiko kehamilan, tekanan darah, dan jumlah ibu hamil yang dipantau.",
            "B": "Harga obat di apotek sekitar.",
            "C": "Jadwal keberangkatan transportasi umum.",
            "D": "Data kependudukan seluruh kecamatan."
        },
        "answer": "A"
    },
    {
        "no": 5,
        "question": "Mengapa otomatisasi data riwayat kesehatan dan visualisasi risiko pada dashboard sangat krusial dalam mendukung pelayanan KIA (Kesehatan Ibu dan Anak)?",
        "options": {
            "A": "Agar kader Posyandu bisa mengambil keputusan Rujukan Dini Berencana (RDB) secara tepat waktu demi menekan Angka Kematian Ibu (AKI).",
            "B": "Agar ibu hamil tidak perlu lagi datang memeriksakan kandungan ke fasilitas kesehatan.",
            "C": "Untuk menghapus peran Dokter Spesialis Obgyn dan Bidan Desa secara permanen.",
            "D": "Hanya untuk mengganti pajangan buku register di meja kader."
        },
        "answer": "A"
    }
]

# --- STYLING CSS MEDIS & KONTRAS TINGGI ---
st.markdown(
    """
    <style>
    /* Latar Belakang & Teks Global */
    html, body, .stApp, [data-testid="stAppViewContainer"] {
        background-color: #f8fafc !important;
        color: #1e293b !important;
    }

    /* Header & Judul Utama */
    h1, h2, h3, h4, h5, h6,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4,
    [data-testid="stHeadingWithActionElements"] h1,
    [data-testid="stHeadingWithActionElements"] h2,
    [data-testid="stHeadingWithActionElements"] h3 {
        color: #064e3b !important;
        font-weight: 700 !important;
    }

    p, span, div, .stMarkdown {
        color: #1e293b !important;
    }

    .stCaption, [data-testid="stCaptionContainer"] p, small {
        color: #475569 !important;
        font-size: 0.88rem !important;
    }

    [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] p {
        color: #0f172a !important;
        font-weight: 600 !important;
    }

    /* Input & Kotak Tanggal */
    input, textarea,
    [data-testid="stTextInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stNumberInput"] input,
    [data-baseweb="input"],
    [data-baseweb="base-input"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
    }

    [data-testid="stDateInput"] div,
    [data-testid="stDateInput"] input {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }

    /* Kalender Popover & Datepicker */
    div[data-baseweb="popover"],
    div[data-baseweb="calendar"],
    div[role="dialog"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="calendar"] *,
    div[data-baseweb="calendar"] button,
    div[data-baseweb="calendar"] span,
    div[data-baseweb="calendar"] select,
    div[data-baseweb="popover"] * {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }

    div[data-baseweb="calendar"] [role="gridcell"],
    div[data-baseweb="calendar"] [role="gridcell"] div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        font-weight: 600 !important;
    }

    div[data-baseweb="calendar"] [aria-selected="true"],
    div[data-baseweb="calendar"] [aria-selected="true"] * {
        background-color: #059669 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 50% !important;
    }

    /* Badge Tag Kategori & Filter */
    [data-baseweb="tag"],
    span[data-baseweb="tag"] {
        background-color: #ecfdf5 !important;
        border: 1px solid #a7f3d0 !important;
        border-radius: 6px !important;
        padding: 2px 6px !important;
    }
    [data-baseweb="tag"] *,
    span[data-baseweb="tag"] * {
        background-color: transparent !important;
        color: #064e3b !important;
        font-weight: 600 !important;
        fill: #064e3b !important;
    }

    /* Slider Usia & Tombol Angka */
    [data-testid="stSlider"] div[role="slider"] {
        background-color: #059669 !important;
        border-color: #059669 !important;
    }
    [data-testid="stSlider"] [data-testid="stThumbValue"] {
        color: #064e3b !important;
        font-weight: 700 !important;
    }
    [data-testid="stNumberInput"] button {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
    }

    /* Kartu Metrik */
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        padding: 14px 16px !important;
    }
    [data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] div, [data-testid="stMetricValue"] {
        color: #064e3b !important;
        font-weight: 800 !important;
    }

    /* Tombol */
    button[kind="primary"] {
        background-color: #059669 !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
    }
    button[kind="secondary"] {
        background-color: #ffffff !important;
        color: #064e3b !important;
        border: 1px solid #cbd5e1 !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
    }

    /* Radio button options */
    div[role="radiogroup"] label {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 6px !important;
        padding: 6px 12px !important;
        margin-bottom: 6px !important;
    }
    div[role="radiogroup"] label * {
        color: #0f172a !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_auth_config():
    try:
        auth_secrets = st.secrets.get("auth", {})
    except (FileNotFoundError, KeyError):
        auth_secrets = {}
    return {
        "email": auth_secrets.get("email") or os.getenv("MATERNALCARE_EMAIL", ""),
        "password_hash": auth_secrets.get("password_hash")
        or os.getenv("MATERNALCARE_PASSWORD_HASH", ""),
    }


def password_matches(password, password_hash):
    candidate_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(candidate_hash, str(password_hash))


def render_login():
    if st.session_state.get("authenticated"):
        return True

    auth_config = get_auth_config()

    st.markdown("### Selamat Datang di Posyandu Kamboja Cadas Tangerang")
    st.title("Sign in")
    st.caption("Masuk untuk mengakses Dashboard Pemantauan Kehamilan.")

    with st.form("login_form"):
        email = st.text_input("User", autocomplete="username")
        password = st.text_input(
            "Password", type="password", autocomplete="current-password"
        )
        submitted = st.form_submit_button("Sign in", type="primary")

    if submitted:
        if not auth_config["email"] or not auth_config["password_hash"]:
            st.error(
                "Login belum dikonfigurasi. Isi auth.email dan auth.password_hash "
                "di Streamlit secrets atau environment variable."
            )
            return False
        valid_email = hmac.compare_digest(
            email.strip().casefold(), str(auth_config["email"]).strip().casefold()
        )
        if valid_email and password_matches(password, auth_config["password_hash"]):
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Email atau password tidak valid.")
    return False


if not render_login():
    st.stop()


def classify_score(score):
    if pd.isna(score):
        return "Perlu verifikasi"
    if score == 2:
        return "KRR"
    if 6 <= score <= 10:
        return "KRT"
    if score >= 12:
        return "KRST"
    return "Perlu verifikasi"


def blood_pressure_status(row):
    systolic = row.get("tekanan_darah_sistol")
    diastolic = row.get("tekanan_darah_diastol")
    if pd.isna(systolic) or pd.isna(diastolic):
        return "Dalam rentang pemantauan"
    if systolic >= 160 or diastolic >= 110:
        return "Perlu penilaian segera"
    if systolic >= 140 or diastolic >= 90:
        return "Perlu evaluasi"
    return "Dalam rentang pemantauan"


def get_api_url():
    try:
        return st.secrets.get("google_sheets", {}).get("api_url") or os.getenv("GOOGLE_SHEETS_API_URL", "")
    except Exception:
        return os.getenv("GOOGLE_SHEETS_API_URL", "")


@st.cache_data(ttl=60)
def load_data():
    api_url = get_api_url()
    df = None
    if api_url:
        try:
            res = requests.get(api_url, timeout=12)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len
