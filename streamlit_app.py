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

    /* Kartu Metrik (Disesuaikan agar teks kategori tidak terpotong) */
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
        font-size: 1.65rem !important;
        white-space: normal !important;
        word-break: normal !important;
        text-overflow: unset !important;
        line-height: 1.2 !important;
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
        ["KRR (Risiko Rendah)", "Skor = 2", counts.get("KRR", 0), percent(counts.get("KRR", 0), total), "Bidan di Polindes, Puskesmas, atau BPM Mandiri"],
        ["KRT (Risiko Tinggi)", "Skor 6 - 10", counts.get("KRT", 0), percent(counts.get("KRT", 0), total), "Bidan didampingi Dokter di Puskesmas / Rujukan Terencana RS"],
        ["KRST (Risiko Sgt Tinggi)", "Skor >= 12", counts.get("KRST", 0), percent(counts.get("KRST", 0), total), "Wajib di Rumah Sakit PONEK bersama Dokter Spesialis Obgyn"],
        ["TOTAL", "-", total, "100.0%" if total else "0.0%", "-"],
    ]
    risk_table = Table([[paragraph(cell, small_style) for cell in row] for row in risk_rows], colWidths=[29 * mm, 23 * mm, 21 * mm, 23 * mm, 75 * mm], repeatRows=1)
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#183e35")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9aa9a0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.extend([risk_table, Paragraph("3. Faktor Risiko Klinis & Komorbiditas Dominan", heading_style)])
    factor_rows = [
        ["Faktor Risiko / Komplikasi", "Jumlah Kasus", "Prevalensi (%)", "Dampak & Catatan Klinis"],
        ["Tekanan Darah Tinggi / Hipertensi (>=140/90 mmHg)", hypertension, percent(hypertension, total), "Perlu pemantauan tekanan darah dan evaluasi risiko preeklamsia."],
        ["Usia Rentan Reproduksi (<20 th atau >=35 th)", age_risk, percent(age_risk, total), "Perlu pemantauan khusus sesuai faktor usia ibu."],
        ["Risiko Panggul Sempit (Tinggi Badan <145 cm)", short_pelvis, percent(short_pelvis, total), "Perlu perhatian terhadap potensi disproporsi kepala panggul."],
        ["Riwayat Bekas Operasi Caesar (SC)", caesarean, percent(caesarean, total), "Evaluasi rencana persalinan dan risiko ruptur uteri."],
    ]
    factor_table = Table([[paragraph(cell, small_style) for cell in row] for row in factor_rows], colWidths=[57 * mm, 22 * mm, 22 * mm, 70 * mm], repeatRows=1)
    factor_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#183e35")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9aa9a0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(factor_table)
    disease_text = ", ".join(f"{name} ({count} kasus)" for name, count in disease_values.items()) or "Tidak ada data penyakit yang tercatat"
    allergy_text = ", ".join(f"{name} ({count} kasus)" for name, count in allergy_values.items()) or "Tidak ada data alergi yang tercatat"
    elements.extend([
        paragraph(f"Riwayat Penyakit Terbanyak: {disease_text}."),
        paragraph(f"Riwayat Alergi Terbanyak: {allergy_text}."),
        PageBreak(),
        Paragraph("4. Rekomendasi Tindak Lanjut Program Kesehatan Ibu", heading_style),
        paragraph("Bagi Kader Posyandu: Pemasangan stiker P4K di rumah seluruh ibu hamil, pendampingan kepatuhan konsumsi 90 Tablet Tambah Darah (TTD) dan kalsium, serta pemantauan donor darah keluarga siaga."),
        paragraph(f"Bagi Bidan & Puskesmas: Penguatan skrining preeklamsia terpadu pada {hypertension} ibu bertekanan darah tinggi. Koordinasi Rujukan Dini Berencana (RDB) bagi {counts.get('KRST', 0)} ibu hamil KRST sebelum timbul tanda inpartu."),
        paragraph("Bagi Rumah Sakit Rujukan (PONEK): Kesiapsiagaan fasilitas penanganan gawat darurat obstetri neonatal 24 jam, ketersediaan darah, dan penjadwalan persalinan terencana pada kasus bekas SC dan disproporsi panggul."),
        Spacer(1, 14 * mm),
        paragraph("Mengetahui,"), Spacer(1, 15 * mm), paragraph("Koordinator Bidan Puskesmas"),
        paragraph("___________________________"), paragraph("NIP. ...................................."),
        Spacer(1, 8 * mm), paragraph("Disusun Oleh,"), Spacer(1, 15 * mm), paragraph("Tim Analis MaternalCare"),
        paragraph("___________________________"), paragraph(f"Tanggal: {generated_at}"),
    ])
    document.build(elements)
    return buffer.getvalue()


def save_patient(record, existing_id=None):
    record = record.copy()
    score, _, unassessed = calculate_poedji_score(record)
    if unassessed:
        raise ValueError("Lengkapi penilaian faktor risiko tambahan terlebih dahulu.")
    record["skor_poedji_rochjati"] = score
    record["kategori_risiko"] = classify_score(score)
    for column in SOURCE_COLUMNS:
        if column not in record:
            record[column] = "Belum dinilai" if column in ADDITIONAL_RISK_COLUMNS else ""

    api_url = get_api_url()
    if not api_url:
        raise ValueError("URL Google Sheets API belum dikonfigurasi di secrets.")

    payload = {
        "existing_id": existing_id,
        "record": {k: ("" if pd.isna(v) else str(v)) for k, v in record.items()}
    }
    res = requests.post(api_url, json=payload, timeout=20)
    if res.status_code not in (200, 302):
        raise ValueError("Gagal menyimpan data ke Google Sheets.")


def render_patient_fields(prefix, patient=None):
    def value(column, fallback):
        if patient is None or column not in patient or pd.isna(patient[column]):
            return fallback
        return patient[column]

    def date_value(column):
        parsed = pd.to_datetime(value(column, date.today()), errors="coerce")
        return parsed.date() if pd.notna(parsed) else date.today()

    identity_columns = st.columns(2)
    with identity_columns[0]:
        patient_id = st.text_input(
            "ID ibu",
            value=str(value("id_ibu", "")),
            disabled=patient is not None,
            key=f"{prefix}_id",
        )
        name = st.text_input(
            "Nama ibu", value=str(value("nama_ibu", "")), key=f"{prefix}_name"
        )
        nik = st.text_input(
            "NIK",
            value=str(value("nik", "")),
            max_chars=32,
            key=f"{prefix}_nik",
        )
        husband = st.text_input(
            "Nama suami",
            value=str(value("nama_suami", "")),
            key=f"{prefix}_husband",
        )
        address = st.text_input(
            "Alamat", value=str(value("alamat", "")), key=f"{prefix}_address"
        )
    with identity_columns[1]:
        age = st.number_input(
            "Usia ibu (tahun)", 10, 60, int(value("usia", 30)), key=f"{prefix}_age"
        )
        birthplace = st.text_input(
            "Tempat lahir",
            value=str(value("tempat_lahir", "")),
            key=f"{prefix}_birthplace",
        )
        birth_date = st.date_input(
            "Tanggal lahir",
            value=date_value("tanggal_lahir"),
            format="DD/MM/YYYY",
            key=f"{prefix}_dob",
        )
        due_date = st.date_input(
            "Hari perkiraan lahir (HPL)",
            value=date_value("hpl"),
            format="DD/MM/YYYY",
            key=f"{prefix}_hpl",
        )
        gestational_age = st.number_input(
            "Usia kehamilan (minggu)",
            0,
            45,
            int(value("usia_hamil_minggu", 20)),
            key=f"{prefix}_gestation",
        )

    history_columns = st.columns(3)
    with history_columns[0]:
        height = st.number_input(
            "Tinggi badan (cm)",
            100,
            220,
            int(value("tinggi_badan_cm", 150)),
            key=f"{prefix}_height",
        )
        pregnancy_gap = st.number_input(
            "Jarak kehamilan (tahun)",
            0,
            50,
            int(value("jarak_kehamilan_tahun", 0)),
            key=f"{prefix}_gap",
        )
        living_children = st.number_input(
            "Jumlah anak hidup",
            0,
            20,
            int(value("jumlah_anak_hidup", 0)),
            key=f"{prefix}_children",
        )
    with history_columns[1]:
        caesarean = st.selectbox(
            "Riwayat operasi caesar",
            [0, 1],
            index=int(value("riwayat_caesar", 0)),
            format_func=lambda option: "Ya" if option else "Tidak",
            key=f"{prefix}_caesarean",
        )
        allergy = st.text_input(
            "Alergi", value=str(value("alergi", "Tidak ada")), key=f"{prefix}_allergy"
        )
        illness = st.text_input(
            "Riwayat penyakit",
            value=str(value("riwayat_sakit", "Tidak ada")),
            key=f"{prefix}_illness",
        )
    with history_columns[2]:
        systolic = st.number_input(
            "Tekanan sistolik (mmHg)",
            50,
            260,
            int(value("tekanan_darah_sistol", 120)),
            key=f"{prefix}_systolic",
        )
        diastolic = st.number_input(
            "Tekanan diastolik (mmHg)",
            30,
            160,
            int(value("tekanan_darah_diastol", 80)),
            key=f"{prefix}_diastolic",
        )

    additional_labels = {
        "riwayat_keguguran": "Pernah keguguran",
        "kehamilan_kembar": "Kehamilan kembar",
        "riwayat_hamil_anggur": "Riwayat hamil anggur",
        "anemia_berat": "Anemia berat (Hb <8 g/dL)",
        "penyakit_kronis": "Penyakit kronis (mis. diabetes/jantung/asma)",
        "kelainan_letak_janin": "Letak janin sungsang/lintang",
        "perdarahan_kehamilan": "Perdarahan antepartum",
        "preeklamsia_berat": "Preeklamsia berat/eklamsia",
    }
    st.markdown("#### Faktor risiko tambahan")
    additional_columns = st.columns(4)
    additional_values = {}
    assessment_options = ["Belum dinilai", "Tidak", "Ya"]
    for index, column in enumerate(ADDITIONAL_RISK_COLUMNS):
        with additional_columns[index % len(additional_columns)]:
            current_value = str(value(column, "Belum dinilai"))
            additional_values[column] = st.selectbox(
                additional_labels[column],
                assessment_options,
                index=(
                    assessment_options.index(current_value)
                    if current_value in assessment_options
                    else 0
                ),
                key=f"{prefix}_{column}",
            )

    record = {
        "usia": int(age),
        "tinggi_badan_cm": int(height),
        "jarak_kehamilan_tahun": int(pregnancy_gap),
        "jumlah_anak_hidup": int(living_children),
        "riwayat_caesar": int(caesarean),
        "tekanan_darah_sistol": int(systolic),
        "tekanan_darah_diastol": int(diastolic),
        **additional_values,
    }
    score, factors, unassessed = calculate_poedji_score(record)
    st.metric("Skor Poedji Rochjati", score)
    category = "Perlu verifikasi" if unassessed else classify_score(score)
    st.caption(f"Kategori otomatis: {category}")
    if factors:
        st.caption("Faktor yang menambah skor: " + ", ".join(label for label, _ in factors))
    if unassessed:
        st.warning("Nilai skor belum final. Lengkapi faktor tambahan yang belum dinilai.")

    return {
        "id_ibu": patient_id.strip(),
        "nama_ibu": name.strip(),
        "nik": nik.strip(),
        "nama_suami": husband.strip(),
        "usia": int(age),
        "tempat_lahir": birthplace.strip(),
        "tanggal_lahir": birth_date.isoformat(),
        "hpl": due_date.isoformat(),
        "usia_hamil": f"{int(gestational_age)} minggu",
        "alamat": address.strip(),
        "alergi": allergy.strip() or "Tidak ada",
        "riwayat_sakit": illness.strip() or "Tidak ada",
        "tinggi_badan_cm": int(height),
        "jarak_kehamilan_tahun": int(pregnancy_gap),
        "jumlah_anak_hidup": int(living_children),
        "riwayat_caesar": int(caesarean),
        "tekanan_darah_sistol": int(systolic),
        "tekanan_darah_diastol": int(diastolic),
        **additional_values,
        "skor_poedji_rochjati": score,
        "kategori_risiko": category,
    }


# --- FUNGSI DATA EVALUASI KADER ---
def load_eval_data():
    if EVAL_FILE.exists():
        try:
            return pd.read_csv(EVAL_FILE)
        except Exception:
            pass
    return pd.DataFrame(
        columns=[
            "timestamp", "nama_kader", "jenis_tes", "wilayah",
            "skor", "jumlah_benar", "jawaban_1", "jawaban_2",
            "jawaban_3", "jawaban_4", "jawaban_5"
        ]
    )


def save_eval_record(record):
    df_eval = load_eval_data()
    df_eval = pd.concat([df_eval, pd.DataFrame([record])], ignore_index=True)
    df_eval.to_csv(EVAL_FILE, index=False)


df = load_data()

# --- SIDEBAR & NAVIGASI MENU ---
with st.sidebar:
    st.markdown("### POSYANDU KAMBOJA")
    st.caption("Pemantauan risiko kehamilan & Evaluasi KIA")
    if st.button("Keluar", key="logout_button"):
        st.session_state["authenticated"] = False
        st.rerun()

    st.markdown("---")
    menu = st.radio(
        "Pilih Menu:",
        ["📊 Dashboard Monitoring", "📝 Evaluasi Kader (Pre/Post Test)"],
        index=0,
        key="main_menu_nav"
    )
    st.markdown("---")


# =========================================================================
# MENU 1: DASHBOARD MONITORING KEHAMILAN
# =========================================================================
if menu == "📊 Dashboard Monitoring":
    with st.sidebar:
        search = st.text_input("Cari nama atau ID ibu", placeholder="Contoh: Ibu-001")
        selected_risks = st.multiselect(
            "Kategori KSPR",
            RISK_ORDER,
            default=RISK_ORDER[:3],
        )
        locations = sorted(df["alamat"].dropna().unique().tolist())
        selected_locations = st.multiselect("Wilayah", locations)

        if "usia_hamil" in df.columns:
            df["usia_hamil_minggu"] = (
                df["usia_hamil"].astype(str).str.extract(r"(\d+)").astype(float)
            )

        if "usia_hamil_minggu" in df.columns and not df["usia_hamil_minggu"].isna().all():
            min_week = int(df["usia_hamil_minggu"].min())
            max_week = int(df["usia_hamil_minggu"].max())
        else:
            min_week, max_week = 4, 40

        selected_weeks = st.slider(
            "Usia kehamilan (minggu)",
            min_value=min_week,
            max_value=max_week,
            value=(min_week, max_week),
        )

    target_col = "kategori_risiko" if "kategori_risiko" in df.columns else "kategori_kspr"
    cond_risk = df[target_col].isin(selected_risks)
    cond_week = df["usia_hamil_minggu"].between(selected_weeks[0], selected_weeks[1])

    filtered = df[cond_risk & cond_week].copy()

    if selected_locations:
        filtered = filtered[filtered["alamat"].isin(selected_locations)]
    if search.strip():
        query = search.strip().casefold()
        filtered = filtered[
            filtered["nama_ibu"].astype(str).str.casefold().str.contains(query, na=False)
            | filtered["id_ibu"].astype(str).str.casefold().str.contains(query, na=False)
        ]

    st.title("MONITORING KEHAMILAN KAMBOJA 2B")
    st.caption(
        "Ringkasan ibu hamil, skor Poedji Rochjati, dan tindak lanjut tekanan darah."
    )

    kategori_col = "kategori_risiko" if "kategori_risiko" in filtered.columns else "kategori_kspr"
    total = len(filtered)
    counts = filtered[kategori_col].value_counts()

    if "status_tekanan_darah" in filtered.columns:
        urgent_bp = filtered["status_tekanan_darah"].eq("Perlu penilaian segera").sum()
        needs_review = filtered["status_tekanan_darah"].eq("Perlu evaluasi").sum()
    else:
        urgent_bp = ((filtered["tekanan_darah_sistol"] >= 160) | (filtered["tekanan_darah_diastol"] >= 110)).sum()
        needs_review = ((filtered["tekanan_darah_sistol"] >= 140) | (filtered["tekanan_darah_diastol"] >= 90)).sum() - urgent_bp

    report_table = filtered[
        [
            "id_ibu",
            "nama_ibu",
            "usia",
            "usia_hamil_minggu",
            "hpl_date",
            "tekanan_darah",
            "status_tekanan_darah",
            "skor_poedji_rochjati",
            "kategori_kspr",
        ]
    ].copy()
    report_table = report_table.rename(
        columns={
            "id_ibu": "ID",
            "nama_ibu": "Nama ibu",
            "usia": "Usia",
            "usia_hamil_minggu": "Usia hamil (minggu)",
            "hpl_date": "HPL",
            "tekanan_darah": "TD (mmHg)",
            "status_tekanan_darah": "Status TD",
            "skor_poedji_rochjati": "Skor KSPR",
            "kategori_kspr": "Kategori",
        }
    )
    report_table["HPL"] = report_table["HPL"].dt.strftime("%d %b %Y").fillna("-")
    downloaded_at = datetime.now()
    downloaded_at_label = downloaded_at.strftime("%d %B %Y, %H:%M:%S")
    downloaded_at_file = downloaded_at.strftime("%Y-%m-%d_%H-%M-%S")

    download_columns = st.columns(2)
    with download_columns[0]:
        st.download_button(
            "Unduh laporan PDF terbaru",
            data=build_report_pdf(filtered, downloaded_at_label),
            file_name=f"laporan_pemantauan_{downloaded_at_file}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with download_columns[1]:
        st.download_button(
            "Unduh hasil filter (CSV)",
            data=report_table.to_csv(index=False).encode("utf-8-sig"),
            file_name="laporan_pemantauan_kehamilan.csv",
            mime="text/csv",
            use_container_width=True,
        )

    metric_columns = st.columns(5)
    metric_columns[0].metric(
        "Ibu terpantau", f"{total:,}", "100% dari hasil filter", delta_color="off"
    )

    def filtered_percentage(count):
        return count / total * 100 if total else 0

    metric_columns[1].metric(
        "KRR · Risiko rendah",
        f"{counts.get('KRR', 0):,}",
        f"{filtered_percentage(counts.get('KRR', 0)):.1f}% dari total",
        delta_color="off",
    )
    metric_columns[2].metric(
        "KRT · Risiko tinggi",
        f"{counts.get('KRT', 0):,}",
        f"{filtered_percentage(counts.get('KRT', 0)):.1f}% dari total",
        delta_color="off",
    )
    metric_columns[3].metric(
        "KRST · Risiko sangat tinggi",
        f"{counts.get('KRST', 0):,}",
        f"{filtered_percentage(counts.get('KRST', 0)):.1f}% dari total",
        delta_color="off",
    )
    attention_count = urgent_bp + needs_review
    metric_columns[4].metric(
        "Tekanan darah perlu perhatian",
        f"{attention_count:,}",
        f"{filtered_percentage(attention_count):.1f}% dari total",
        delta_color="off",
    )

    illness_values = filtered["riwayat_sakit"].astype("string").str.strip()
    illness_mask = illness_values.notna() & ~illness_values.str.casefold().isin(
        ["", "tidak ada", "belum dinilai", "-"]
    )
    caesarean_mask = pd.to_numeric(filtered["riwayat_caesar"], errors="coerce").eq(1)
    combined_history_mask = illness_mask & caesarean_mask
    combined_history_count = combined_history_mask.sum()
    st.metric(
        "Memiliki riwayat sakit dan operasi Caesar",
        f"{combined_history_count:,}",
        f"{filtered_percentage(combined_history_count):.1f}% dari total",
        delta_color="off",
    )
    st.caption(
        f"Rincian: {illness_mask.sum():,} memiliki riwayat sakit · "
        f"{caesarean_mask.sum():,} memiliki riwayat operasi Caesar. "
        "Metrik menghitung ibu yang memenuhi kedua kondisi sekaligus."
    )
    if st.button(
        "Lihat data riwayat sakit dan Caesar",
        key="toggle_history_records",
        disabled=combined_history_count == 0,
    ):
        st.session_state["show_history_records"] = not st.session_state.get(
            "show_history_records", False
        )

    if st.session_state.get("show_history_records", False):
        history_table = filtered.loc[
            combined_history_mask,
            ["id_ibu", "nama_ibu", "riwayat_sakit", "riwayat_caesar"],
        ].copy()
        history_table = history_table.rename(
            columns={
                "id_ibu": "ID",
                "nama_ibu": "Nama ibu",
                "riwayat_sakit": "Riwayat sakit",
                "riwayat_caesar": "Riwayat operasi Caesar",
            }
        )
        history_table["Riwayat operasi Caesar"] = pd.to_numeric(
            history_table["Riwayat operasi Caesar"], errors="coerce"
        ).map({1: "Ya", 0: "Tidak"}).fillna("Belum dinilai")
        st.subheader(f"Data riwayat sakit dan Caesar ({len(history_table)} ibu)")
        st.dataframe(history_table, hide_index=True, width="stretch")

    st.caption("Pilih kategori untuk melihat nama ibu yang termasuk di dalamnya.")
    category_columns = st.columns(3)
    for index, (category, description) in enumerate(
        [("KRR", "Risiko rendah"), ("KRT", "Risiko tinggi"), ("KRST", "Risiko sangat tinggi")]
    ):
        category_count = int(counts.get(category, 0))
        with category_columns[index]:
            if st.button(
                f"Lihat nama {category} · {description}",
                key=f"show_names_{category}",
                disabled=category_count == 0,
                use_container_width=True,
            ):
                st.session_state["selected_risk_category"] = category

selected_category = st.session_state.get("selected_risk_category")
if selected_category:
    selected_rows = report_table.loc[
        filtered[kategori_col].eq(selected_category),
        ["ID", "Nama ibu", "Usia", "Usia hamil (minggu)", "Skor KSPR", "Kategori"],
    ]
    st.subheader(
        f"Daftar ibu kategori {selected_category} "
        f"({len(selected_rows)} ibu, {filtered_percentage(len(selected_rows)):.1f}%)"
    )
    if selected_rows.empty:
        st.info("Tidak ada ibu pada kategori ini di hasil filter saat ini.")
    else:
        st.dataframe(selected_rows, hide_index=True, width="stretch")
    if st.button("Tutup daftar kategori", key="close_category_names"):
        del st.session_state["selected_risk_category"]
        st.rerun()

    if urgent_bp:
        st.error(
            f"{urgent_bp} ibu memiliki tekanan darah ≥160 sistolik atau ≥110 diastolik. "
            "Tinjau hasil ukur dan ikuti protokol rujukan setempat segera."
        )
    elif needs_review:
        st.warning(
            f"{needs_review} ibu memiliki tekanan darah ≥140 sistolik atau ≥90 diastolik. "
            "Perlu evaluasi oleh tenaga kesehatan."
        )

    st.subheader("Sebaran risiko")
    chart_column, detail_column = st.columns([1, 1.5])
    with chart_column:
        risk_counts = (
            filtered[kategori_col]
            .value_counts()
            .reindex(RISK_ORDER, fill_value=0)
            .rename_axis("Kategori")
            .to_frame("Jumlah ibu")
        )
        st.bar_chart(risk_counts, color="#39816f", height=260)
    with detail_column:
        st.markdown("#### Dasar pembacaan KSPR")
        st.markdown(
            "Skor **2**: KRR · skor **6–10**: KRT · skor **≥12**: KRST. "
            "Kategori pada dashboard diturunkan dari skor yang tersimpan. "
            "Nilai atau kategori sumber yang tidak sesuai rentang ditandai untuk verifikasi."
        )
        st.caption(
            "Dashboard memakai skor KSPR dari dataset, bukan menghitung ulang faktor klinis. "
            "Label sumber KBR pada skor 2 dipetakan ke KRR."
        )

    st.subheader("Daftar pemantauan")
    if filtered.empty:
        st.info("Tidak ada data yang sesuai dengan filter.")
    else:
        table = filtered[
            [
                "id_ibu",
                "nama_ibu",
                "usia",
                "usia_hamil_minggu",
                "hpl_date",
                "tekanan_darah",
                "status_tekanan_darah",
                "skor_poedji_rochjati",
                "kategori_kspr",
            ]
        ].copy()
        table = table.rename(
            columns={
                "id_ibu": "ID",
                "nama_ibu": "Nama ibu",
                "usia": "Usia",
                "usia_hamil_minggu": "Usia hamil (mg) ",
                "hpl_date": "HPL",
                "tekanan_darah": "TD (mmHg)",
                "status_tekanan_darah": "Status TD",
                "skor_poedji_rochjati": "Skor KSPR",
                "kategori_kspr": "Kategori",
            }
        )
        table["HPL"] = table["HPL"].dt.strftime("%d %b %Y").fillna("-")
        st.dataframe(table, hide_index=True, width="stretch", height=360)

        patient_options = filtered.sort_values("nama_ibu")["id_ibu"].tolist()
        patient_by_id = filtered.set_index("id_ibu", drop=False)
        selected_id = st.selectbox(
            "Lihat ringkasan ibu",
            patient_options,
            format_func=lambda patient_id: (
                f"{patient_by_id.at[patient_id, 'nama_ibu']} · {patient_id}"
            ),
        )
        patient = patient_by_id.loc[selected_id]

        st.markdown("#### Ringkasan pasien")
        profile_columns = st.columns(4)
        profile_columns[0].metric("Skor KSPR", f"{int(patient['skor_poedji_rochjati'])}")
        profile_columns[1].metric("Kategori", patient[kategori_col])
        profile_columns[2].metric("Usia kehamilan", f"{int(patient['usia_hamil_minggu'])} minggu")
        profile_columns[3].metric("HPL", display_date(patient["hpl_date"]))

        info_columns = st.columns(3)
        with info_columns[0]:
            st.markdown(f"**Ibu:** {patient['nama_ibu']} ({patient['usia']} tahun)")
            st.markdown(f"**Wilayah:** {patient['alamat']}")
        with info_columns[1]:
            st.markdown(f"**Tekanan darah:** {patient['tekanan_darah']} mmHg")
            st.markdown(f"**Status:** {patient['status_tekanan_darah']}")
        with info_columns[2]:
            st.markdown(f"**Riwayat kesehatan:** {patient['riwayat_sakit']}")
            st.markdown(f"**Alergi:** {patient['alergi']}")

    st.caption(
        "Informasi dashboard membantu pemantauan, bukan diagnosis. "
        "Keputusan klinis dan rujukan tetap dilakukan oleh bidan atau dokter."
    )

    st.divider()
    st.subheader("Kelola data ibu")
    st.warning(
        "Dataset memuat NIK dan informasi kesehatan. Batasi akses dashboard dan file CSV "
        "kepada petugas berwenang; aplikasi ini belum memiliki autentikasi pengguna."
    )

    new_tab, edit_tab = st.tabs(["Tambah ibu baru", "Perbarui data"])
    with new_tab:
        new_prefix = f"new_{st.session_state.get('new_form_version', 0)}"
        st.caption("Lengkapi identitas, informasi kehamilan, tekanan darah, dan faktor risiko.")
        new_record = render_patient_fields(new_prefix)
        add_submitted = st.button("Simpan ibu baru", type="primary", key="add_patient_submit")

        if add_submitted:
            if not new_record["id_ibu"] or not new_record["nama_ibu"] or not new_record["nik"]:
                st.error("ID ibu, nama ibu, dan NIK wajib diisi.")
            else:
                try:
                    save_patient(new_record)
                    load_data.clear()
                    st.session_state["new_form_version"] = (
                        st.session_state.get("new_form_version", 0) + 1
                    )
                    st.success("Data ibu baru berhasil disimpan.")
                    st.rerun()
                except (OSError, ValueError) as error:
                    st.error(f"Data belum tersimpan: {error}")

    with edit_tab:
        edit_options = df.sort_values("nama_ibu")["id_ibu"].tolist()
        edit_by_id = df.set_index("id_ibu", drop=False)
        edit_id = st.selectbox(
            "Pilih ibu",
            edit_options,
            format_func=lambda patient_id: (
                f"{edit_by_id.at[patient_id, 'nama_ibu']} · {patient_id}"
            ),
            key="edit_patient_selector",
        )
        st.caption("ID ibu dikunci untuk menjaga keterkaitan catatan.")
        edited_record = render_patient_fields(
            f"edit_{edit_id}", edit_by_id.loc[edit_id]
        )
        update_submitted = st.button(
            "Simpan perubahan", type="primary", key="update_patient_submit"
        )

        if update_submitted:
            if not edited_record["nama_ibu"] or not edited_record["nik"]:
                st.error("Nama ibu dan NIK wajib diisi.")
            else:
                try:
                    save_patient(edited_record, existing_id=edit_id)
                    load_data.clear()
                    st.success("Perubahan data berhasil disimpan.")
                    st.rerun()
                except (OSError, ValueError) as error:
                    st.error(f"Perubahan belum tersimpan: {error}")


# =========================================================================
# MENU 2: EVALUASI KADER POSYANDU (PRE-TEST & POST-TEST)
# =========================================================================
elif menu == "📝 Evaluasi Kader (Pre/Post Test)":
    st.title("EVALUASI PEMAHAMAN KADER POSYANDU")
    st.caption(
        "Kuesioner Pre-Test dan Post-Test untuk mengukur efektivitas pelatihan "
        "dan penerapan Platform Dashboard Pemantauan Kehamilan."
    )

    test_tab, rekap_tab = st.tabs(["📝 Lembar Kuesioner (Pre/Post Test)", "📊 Rekapitulasi Nilai & Laporan PKM"])

    with test_tab:
        st.markdown("#### Identitas Kader / Peserta")
        id_cols = st.columns(3)
        with id_cols[0]:
            nama_kader = st.text_input("Nama Lengkap Kader *", placeholder="Contoh: Ibu Siti Rahayu")
        with id_cols[1]:
            jenis_tes = st.selectbox(
                "Jenis Evaluasi *",
                ["Pre-Test (Sebelum Pelatihan/Penyuluhan)", "Post-Test (Setelah Pelatihan/Penyuluhan)"],
                index=0,
                key="eval_jenis_tes_select"
            )
        with id_cols[2]:
            wilayah_kader = st.text_input("Posyandu / Wilayah RT *", value="Posyandu Kamboja 2B")

        st.markdown("---")
        st.markdown("#### Soal Evaluasi Pengetahuan")
        st.caption("Pilihlah salah satu jawaban yang paling tepat untuk masing-masing pertanyaan di bawah ini:")

        # Memisahkan key radio button antara Pre-Test dan Post-Test agar otomatis bersih saat berpindah opsi
        test_key = "post" if "Post-Test" in jenis_tes else "pre"
        eval_session = st.session_state.get("eval_session", 0)

        selected_answers = {}
        for q in EVALUATION_QUESTIONS:
            st.markdown(f"**Soal {q['no']}. {q['question']}**")
            options_list = [
                f"A. {q['options']['A']}",
                f"B. {q['options']['B']}",
                f"C. {q['options']['C']}",
                f"D. {q['options']['D']}",
            ]
            choice = st.radio(
                f"Jawaban untuk Soal {q['no']}:",
                options_list,
                index=None,
                key=f"eval_q_{q['no']}_{test_key}_{eval_session}"
            )
            selected_answers[q['no']] = choice[0] if choice else None
            st.markdown("<br/>", unsafe_allow_html=True)

        submit_test = st.button("Kirim Jawaban & Hitung Skor", type="primary", use_container_width=True)

        if submit_test:
            if not nama_kader.strip():
                st.error("Mohon isi Nama Lengkap Kader sebelum mengirimkan jawaban.")
            elif any(ans is None for ans in selected_answers.values()):
                st.warning("Mohon jawab seluruh 5 soal evaluasi sebelum mengirimkan.")
            else:
                correct_count = sum(1 for q in EVALUATION_QUESTIONS if selected_answers[q["no"]] == q["answer"])
                score = int((correct_count / len(EVALUATION_QUESTIONS)) * 100)
                is_post_test = "Post-Test" in jenis_tes

                record_test = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "nama_kader": nama_kader.strip(),
                    "jenis_tes": "Post-Test" if is_post_test else "Pre-Test",
                    "wilayah": wilayah_kader.strip(),
                    "skor": score,
                    "jumlah_benar": correct_count,
                    "jawaban_1": selected_answers[1],
                    "jawaban_2": selected_answers[2],
                    "jawaban_3": selected_answers[3],
                    "jawaban_4": selected_answers[4],
                    "jawaban_5": selected_answers[5],
                }
                save_eval_record(record_test)

                # HASIL LANGSUNG TAMPIL TEPAT DI BAWAH TOMBOL (KOTAK KETIGA LEBIH LEBAR)
                st.markdown("---")
                st.success(f"Selamat, {nama_kader}! Jawaban {record_test['jenis_tes']} Anda berhasil dikirim dan tersimpan.")

                res_cols = st.columns([1, 1, 1.4])
                res_cols[0].metric(f"Skor {record_test['jenis_tes']}", f"{score} / 100")
                res_cols[1].metric("Jumlah Jawaban Benar", f"{correct_count} dari 5 soal")
                res_cols[2].metric("Kategori Pemahaman", "Sangat Baik" if score >= 80 else ("Cukup" if score >= 60 else "Perlu Penguatan"))

                if is_post_test:
                    if score >= 80:
                        st.balloons()
                    st.markdown("#### Pembahasan & Kunci Jawaban Post-Test:")
                    for q in EVALUATION_QUESTIONS:
                        user_ans = selected_answers[q["no"]]
                        is_correct = user_ans == q["answer"]
                        if is_correct:
                            st.markdown(f"✅ **Soal {q['no']} (Benar):** Jawaban Anda **{user_ans}** ({q['options'][user_ans]})")
                        else:
                            st.markdown(f"❌ **Soal {q['no']} (Kurang Tepat):** Jawaban Anda **{user_ans}**. Kunci Jawaban: **{q['answer']}. {q['options'][q['answer']]}**")
                else:
                    st.info(
                        "ℹ️ **Terima kasih telah berpartisipasi dalam Pre-Test!**\n\n"
                        "Kunci jawaban dan pembahasan sengaja **tidak ditampilkan pada tahap Pre-Test** "
                        "agar proses evaluasi pemahaman sebelum dan sesudah pelatihan berlangsung objektif. "
                        "Pembahasan lengkap beserta kunci jawaban akan ditampilkan setelah Anda menyelesaikan **Post-Test**."
                    )

                st.markdown("<br/>", unsafe_allow_html=True)
                if st.button("🔄 Selesai & Bersihkan Formulir (Untuk Kader Berikutnya)", key="clear_after_submit"):
                    st.session_state["eval_session"] = eval_session + 1
                    st.rerun()

    with rekap_tab:
        df_rekap = load_eval_data()
        st.subheader("Rekapitulasi Hasil Evaluasi Kader Posyandu")
        st.caption("Data hasil evaluasi tersimpan otomatis dan dapat digunakan sebagai bukti luaran Pengabdian Kepada Masyarakat (PKM).")

        if df_rekap.empty:
            st.info("Belum ada data evaluasi yang masuk. Silakan isi kuesioner pada tab lembar kuesioner.")
        else:
            pre_scores = df_rekap[df_rekap["jenis_tes"] == "Pre-Test"]["skor"]
            post_scores = df_rekap[df_rekap["jenis_tes"] == "Post-Test"]["skor"]

            avg_pre = pre_scores.mean() if not pre_scores.empty else 0
            avg_post = post_scores.mean() if not post_scores.empty else 0
            peningkatan = avg_post - avg_pre if (not pre_scores.empty and not post_scores.empty) else 0

            stat_cols = st.columns(4)
            stat_cols[0].metric("Total Peserta Mengisi", f"{len(df_rekap)} catatan")
            stat_cols[1].metric("Rata-Rata Pre-Test", f"{avg_pre:.1f}")
            stat_cols[2].metric("Rata-Rata Post-Test", f"{avg_post:.1f}")
            stat_cols[3].metric("Kenaikan Skor Rata-rata", f"{peningkatan:+.1f} poin")

            st.markdown("#### Tabel Data Lengkap Responden")
            display_rekap = df_rekap.rename(
                columns={
                    "timestamp": "Waktu",
                    "nama_kader": "Nama Kader",
                    "jenis_tes": "Jenis Tes",
                    "wilayah": "Posyandu/Wilayah",
                    "skor": "Skor",
                    "jumlah_benar": "Benar",
                    "jawaban_1": "Q1",
                    "jawaban_2": "Q2",
                    "jawaban_3": "Q3",
                    "jawaban_4": "Q4",
                    "jawaban_5": "Q5",
                }
            )
            st.dataframe(display_rekap, hide_index=True, width="stretch")

            csv_data = df_rekap.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📥 Unduh Rekap Nilai Evaluasi (CSV)",
                data=csv_data,
                file_name=f"rekap_evaluasi_kader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

            # --- MENU HAPUS / RESET DATA EVALUASI ---
            st.markdown("---")
            with st.expander("🗑️ Pengaturan / Hapus Data Evaluasi"):
                st.caption("Gunakan menu ini jika ingin membersihkan data percobaan sebelum kegiatan resmi dimulai.")
                confirm_del = st.checkbox("Saya yakin ingin mengosongkan / menghapus semua catatan evaluasi di atas.")
                if st.button("Hapus Semua Data Evaluasi", type="secondary", disabled=not confirm_del):
                    if EVAL_FILE.exists():
                        EVAL_FILE.unlink()
                    if "last_eval_result" in st.session_state:
                        del st.session_state["last_eval_result"]
                    st.success("Seluruh data evaluasi berhasil dihapus.")
                    st.rerun()
