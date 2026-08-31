# build_exe.ps1  (v2.3)
#
# Χτίζει ένα αυτόνομο Windows εκτελέσιμο (.exe) από το
# entersoft_wiki_crawler_v2_3.py, ώστε να μπορεί να τρέξει και σε μηχάνημα
# χωρίς εγκατεστημένο Python.
#
# Νέο στο 2.3: το --collect-all playwright συμπεριλαμβάνει μέσα στο .exe
# το εσωτερικό "driver" του Playwright (τον μηχανισμό που κατεβάζει το
# Chromium). Έτσι το .exe μπορεί να ελέγξει/εγκαταστήσει μόνο του το
# Chromium την πρώτη φορά που θα τρέξει σε ένα καινούριο μηχάνημα —
# χωρίς να χρειάζεται καθόλου Python εκεί. Αρκεί σύνδεση internet.
#
# Χρήση:
#   .venv\Scripts\activate
#   pip install -r requirements.txt -r requirements-dev.txt
#   .\build_exe.ps1
#
# Το αποτέλεσμα θα είναι στο: dist\entersoft_wiki_crawler_v2_3.exe

$ErrorActionPreference = "Stop"

Write-Host "[+] Καθαρισμός προηγούμενων build..." -ForegroundColor Cyan
Remove-Item -Recurse -Force build, dist, *.spec -ErrorAction SilentlyContinue

Write-Host "[+] Build με PyInstaller (onefile, με ενσωματωμένο Playwright driver)..." -ForegroundColor Cyan
pyinstaller --onefile `
    --name entersoft_wiki_crawler_v2_3 `
    --console `
    --collect-all playwright `
    entersoft_wiki_crawler_v2_3.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Το build απέτυχε." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[+] Έτοιμο: dist\entersoft_wiki_crawler_v2_3.exe" -ForegroundColor Green
Write-Host "[+] Το .exe θα ελέγξει και θα εγκαταστήσει μόνο του το Chromium" -ForegroundColor Yellow
Write-Host "    την πρώτη φορά που θα τρέξει σε ένα μηχάνημα (χρειάζεται μόνο" -ForegroundColor Yellow
Write-Host "    σύνδεση internet, όχι Python). Αν θες να το παραλείψεις," -ForegroundColor Yellow
Write-Host "    χρησιμοποίησε: --skip-chromium-check" -ForegroundColor Yellow
