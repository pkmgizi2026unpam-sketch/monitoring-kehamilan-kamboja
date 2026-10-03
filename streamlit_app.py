import requests

def get_api_url():
    try:
        return st.secrets.get("google_sheets", {}).get("api_url") or os.getenv("GOOGLE_SHEETS_API_URL", "")
    except Exception:
        return os.getenv("GOOGLE_SHEETS_API_URL", "")

@st.cache_data(ttl=60)
def load_data():
    api_url = get_api_url()
    loaded_from_api = False
    
    if api_url:
        try:
            res = requests.get(api_url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data:
                    df = pd.DataFrame(data)
                    loaded_from_api = True
        except Exception:
            pass

    if not loaded_from_api:
        if DATA_FILE.exists():
            df = pd.read_csv(DATA_FILE)
        else:
            df = pd.DataFrame(columns=SOURCE_COLUMNS)

    for column in SOURCE_COLUMNS:
        if column not in df:
            df[column] = "Belum dinilai" if column in ADDITIONAL_RISK_COLUMNS else ""
    for column in ADDITIONAL_RISK_COLUMNS:
        if column not in df:
            df[column] = "Belum dinilai"

    numeric_columns = [
        "usia", "tinggi_badan_cm", "jarak_kehamilan_tahun",
        "jumlah_anak_hidup", "riwayat_caesar",
        "tekanan_darah_sistol", "tekanan_darah_diastol",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["skor_poedji_rochjati"] = pd.to_numeric(df["skor_poedji_rochjati"], errors="coerce")
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
        "record": record
    }
    res = requests.post(api_url, json=payload, timeout=15)
    if res.status_code != 200:
        raise ValueError("Gagal menyimpan data ke Google Sheets.")
