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
                if isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data)
        except Exception:
            pass

    if df is None or df.empty:
        if DATA_FILE.exists():
            df = pd.read_csv(DATA_FILE)
        else:
            df = pd.DataFrame(columns=SOURCE_COLUMNS)

    for column in SOURCE_COLUMNS:
        if column not in df.columns:
            df[column] = "Belum dinilai" if column in ADDITIONAL_RISK_COLUMNS else ""
    for column in ADDITIONAL_RISK_COLUMNS:
        if column not in df.columns:
            df[column] = "Belum dinilai"

    numeric_columns = [
        "usia",
        "tinggi_badan_cm",
        "jarak_kehamilan_tahun",
        "jumlah_anak_hidup",
        "riwayat_caesar",
        "tekanan_darah_sistol",
        "tekanan_darah_diastol",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["skor_poedji_rochjati"] = pd.to_numeric(
        df["skor_poedji_rochjati"], errors="coerce"
    )
    df["usia_hamil_minggu"] = pd.to_numeric(
        df["usia_hamil"].astype("string").str.extract(r"(\d+)", expand=False),
        errors="coerce",
    )
    df["hpl_date"] = pd.to_datetime(df["hpl"], errors="coerce")
    df["kategori_kspr"] = df["skor_poedji_rochjati"].apply(classify_score)
    df["tekanan_darah"] = (
        df["tekanan_darah_sistol"].fillna(0).astype("int64").astype(str)
        + "/"
        + df["tekanan_darah_diastol"].fillna(0).astype("int64").astype(str)
    )
    df["status_tekanan_darah"] = df.apply(blood_pressure_status, axis=1)
    return df


def calculate_poedji_score(record):
    score = 2
    factors = []

    age = int(record["usia"])
    height = int(record["tinggi_badan_cm"])
    pregnancy_gap = int(record["jarak_kehamilan_tahun"])
    living_children = int(record["jumlah_anak_hidup"])
    systolic = int(record["tekanan_darah_sistol"])
    diastolic = int(record["tekanan_darah_diastol"])

    if age <= 16 or age >= 35:
        factors.append(("Usia ibu berisiko", 4))
    if height < 145:
        factors.append(("Tinggi badan <145 cm", 4))
    if 0 < pregnancy_gap < 2 or pregnancy_gap > 10:
        factors.append(("Jarak kehamilan berisiko", 4))
    if living_children >= 4:
        factors.append(("Jumlah anak hidup >=4", 4))
    if systolic >= 140 or diastolic >= 90:
        factors.append(("Tekanan darah >=140/90 mmHg", 4))
    if int(record["riwayat_caesar"]):
        factors.append(("Riwayat operasi Caesar", 8))

    additional_factors = {
        "riwayat_keguguran": ("Riwayat keguguran", 4),
        "kehamilan_kembar": ("Kehamilan kembar", 4),
        "riwayat_hamil_anggur": ("Riwayat hamil anggur", 4),
        "anemia_berat": ("Anemia berat (Hb <8 g/dL)", 4),
        "penyakit_kronis": ("Penyakit kronis", 4),
        "kelainan_letak_janin": ("Kelainan letak janin", 4),
        "perdarahan_kehamilan": ("Perdarahan antepartum", 8),
        "preeklamsia_berat": ("Preeklamsia berat/eklamsia", 8),
    }
    unassessed = []
    for column, (label, points) in additional_factors.items():
        answer = record.get(column, "Belum dinilai")
        if answer == "Ya":
            factors.append((label, points))
        elif answer != "Tidak":
            unassessed.append(label)

    score += sum(points for _, points in factors)
    return score, factors, unassessed


def display_date(value):
    if pd.isna(value):
        return "Belum tersedia"
    return value.strftime("%d %b %Y")


def build_report_pdf(analysis_data, generated_at):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from xml.sax.saxutils import escape

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=13 * mm, bottomMargin=13 * mm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], alignment=TA_CENTER,
        fontSize=16, leading=19, textColor="#183e35"
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=styles["BodyText"], alignment=TA_CENTER,
        fontSize=9, leading=12
    )
    heading_style = ParagraphStyle(
        "ReportHeading", parent=styles["Heading2"], fontSize=11,
        leading=14, spaceBefore=5 * mm, spaceAfter=2 * mm, textColor="#183e35"
    )
    body_style = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontSize=8.5, leading=11)
    small_style = ParagraphStyle("ReportSmall", parent=body_style, fontSize=7.5, leading=9)

    def paragraph(value, style=body_style):
        return Paragraph(escape(str(value)), style)

    def percent(value, total):
        return f"{value / total * 100:.1f}%" if total else "0.0%"

    def top_values(column):
        if column not in analysis_data.columns:
            return pd.Series(dtype=int)
        values = analysis_data[column].astype("string").str.strip()
        values = values[values.notna() & ~values.str.casefold().isin(["tidak ada", "-", ""])]
        return values.value_counts().head(5)

    total = len(analysis_data)
    kat_col = "kategori_risiko" if "kategori_risiko" in analysis_data.columns else "kategori_kspr"
    counts = analysis_data[kat_col].value_counts()
    hypertension = analysis_data["status_tekanan_darah"].isin(
        ["Perlu evaluasi", "Perlu penilaian segera"]
    ).sum()
    age_risk = ((analysis_data["usia"] < 20) | (analysis_data["usia"] >= 35)).sum()
    short_pelvis = (analysis_data["tinggi_badan_cm"] < 145).sum()
    caesarean = pd.to_numeric(analysis_data["riwayat_caesar"], errors="coerce").fillna(0).eq(1).sum()
    disease_values = top_values("riwayat_sakit")
    allergy_values = top_values("alergi")
    elements = [
        Paragraph("LAPORAN ANALISIS KESELURUHAN SKRINING<br/>KEHAMILAN", title_style),
        Paragraph(
            "Sistem Monitoring Kehamilan Berdasarkan Skoring Poedji Rochjati (KRR, KRT, KRST)",
            subtitle_style,
        ),
        Paragraph("1. Ringkasan Eksekutif", heading_style),
        paragraph(
            f"Laporan ini menyajikan hasil analisis terhadap {total} data ibu hamil "
            f"berdasarkan filter aktif pada dashboard. Berdasarkan sistem skoring Poedji "
            f"Rochjati, terdapat {counts.get('KRT', 0) + counts.get('KRST', 0)} ibu hamil "
            f"({percent(counts.get('KRT', 0) + counts.get('KRST', 0), total)}) dalam kategori "
            f"kehamilan berisiko (KRT dan KRST), sedangkan {counts.get('KRR', 0)} ibu "
            f"({percent(counts.get('KRR', 0), total)}) termasuk Kehamilan Risiko Rendah (KRR)."
        ),
        Paragraph("2. Distribusi Kategori Risiko (Poedji Rochjati)", heading_style),
    ]
    risk_rows = [
        ["Kategori Risiko", "Rentang Skor PR", "Jumlah (Orang)", "Persentase (%)", "Rekomendasi Tempat & Penolong Bersalin"],
        ["KRR (Risiko Rendah)", "Skor
