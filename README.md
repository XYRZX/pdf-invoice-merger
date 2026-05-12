# PDF Invoice Merger (A4 2-up)

This app merges invoice PDFs into fewer A4 pages (2-up), with optional pairing:
- If an invoice and an itinerary belong to the same trip, it places the invoice on top and the itinerary at the bottom.
- Substitute tickets (e.g. folders containing “替票”) are kept as-is and are packed 2-up when possible.

## Language

The app UI automatically follows your system language:
- Supported: Chinese, English, Japanese, Korean, French, Spanish, Russian
- Fallback: English for all other languages

## Features

- Drag & drop PDF files or folders (mixed input supported)
- Auto detection: invoice / itinerary
- Auto crop: removes large blanks and footer page-number area on itinerary pages when possible
- A4 portrait output, packing pages efficiently

## Run (Development)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## Build (macOS)

```bash
chmod +x build_mac.command
./build_mac.command
```

Outputs:
- `dist/InvoiceMerge.app`
- `dist/InvoiceMerge.dmg` (when `packaging/dmgbuild_settings.py` exists)

## Build (Windows)

You cannot reliably build a Windows `.exe` on macOS. Use one of the following:

1) GitHub Actions (recommended)
- Push this repo to GitHub
- Run the workflow at `.github/workflows/build_windows.yml`
- Download the artifact and zip the `dist/InvoiceMerge/` folder for end users

2) Build on a Windows machine
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pyinstaller --noconfirm --clean --windowed --name InvoiceMerge app/main.py
```

Deliver to end users:
- Zip the whole `dist/InvoiceMerge/` folder (do not send only the `.exe`)
