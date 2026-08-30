# build_exe.ps1
#
# Χτίζει ένα αυτόνομο Windows εκτελέσιμο (.exe) από το
# entersoft_wiki_crawler_v2_3.py, ώστε να μπορεί να τρέξει και σε μηχάνημα
# χωρίς εγκατεστημένο Python.
#
# ΝΕΟ στο 2.3: το .exe πλέον ΔΕΝ χρειάζεται πια χειροκίνητο
#     playwright install chromium
# σε κάθε νέο μηχάνημα. Αν το Chromium δεν βρεθεί εγκατεστημένο όταν τρέξει
# το .exe, το κατεβάζει και το εγκαθιστά μόνο του (μία φορά ανά μηχάνημα/
# χρήστη, χρειάζεται απλώς σύνδεση στο internet). Δεν χρειάζεται καθόλου
# Python/pip στο μηχάνημα-στόχο — ΟΥΤΕ καν προσωρινά.
#
# Για να δουλέψει αυτό, το ίδιο το .exe πρέπει να "κουβαλάει" μέσα του τον
# installer/driver του Playwright — αυτό γίνεται παρακάτω με το flag
# "--collect-all playwright" στο PyInstaller (μαζεύει submodules, data
# files ΚΑΙ τα binaries του driver). Χωρίς αυτό το flag, η αυτόματη
# εγκατάσταση chromium μέσα από το .exe θα απέτυχε.
#
# Χρήση (στο μηχάνημα ΤΟΥ DEVELOPER, για να φτιαχτεί το .exe):
#   .venv\Scripts\activate
#   pip install -r requirements.txt -r requirements-dev.txt
#   .\build_exe.ps1
#
# (Δεν χρειάζεται πια να τρέξεις "playwright install chromium" εδώ για να
#  δουλέψει το .exe σε ΑΛΛΑ μηχανήματα — μόνο αν θέλεις να το δοκιμάσεις
#  τοπικά τρέχοντας κατευθείαν το .py.)
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
Write-Host "[+] Το .exe αυτό τρέχει αυτόνομα σε ΟΠΟΙΟΔΗΠΟΤΕ Windows μηχάνημα," -ForegroundColor Yellow
Write-Host "    χωρίς Python/pip. Στην πρώτη εκτέλεση, αν δεν βρει Chromium," -ForegroundColor Yellow
Write-Host "    θα το κατεβάσει/εγκαταστήσει μόνο του αυτόματα (χρειάζεται" -ForegroundColor Yellow
Write-Host "    μόνο σύνδεση internet εκείνη τη στιγμή)." -ForegroundColor Yellow
