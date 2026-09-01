"""
entersoft_wiki_crawler_v2_3.py  (version 2.3)

Αυτόματη λήψη όλων των σελίδων του wiki.entersoft.eu ως PDF, οργανωμένες σε
φακέλους ανά κατηγορία (MediaWiki category) — χωρίς να χρειάζεται να δηλώνεις
χειροκίνητα κάθε κατηγορία.

Πώς δουλεύει:
  1) Ρωτάει το MediaWiki API για ΟΛΕΣ τις κατηγορίες (list=allcategories).
  2) Για κάθε κατηγορία, παίρνει τα μέλη της (list=categorymembers, μόνο
     σελίδες — όχι αρχεία/υποκατηγορίες).
  3) Διαβάζει το manifest.csv από προηγούμενο run (αν υπάρχει) και θεωρεί
     ήδη-κατεβασμένη κάθε σελίδα που είχε status "ok" — ΤΗΝ ΠΡΟΣΠΕΡΝΑΕΙ,
     εκτός αν λείπει το αρχείο από τον δίσκο (τότε την ξανακατεβάζει, ως
     ασφάλεια αν έχει σβηστεί χειροκίνητα) ή αν έχει "μπαγιατέψει" σύμφωνα
     με το --refresh-after (βλ. παρακάτω).
  4) Ανοίγει κάθε ΝΕΑ/ΜΠΑΓΙΑΤΙΚΗ σελίδα σε headless Chromium (Playwright) και
     την αποθηκεύει ως PDF μέσα στον φάκελο της κατηγορίας.
  5) Αν μια σελίδα ανήκει σε πολλές κατηγορίες, αποθηκεύεται ΜΙΑ φορά (στην
     πρώτη κατηγορία που τη συναντάει) — στις υπόλοιπες καταγράφεται μόνο
     αναφορά στο manifest, ώστε να μην υπάρχουν διπλότυπα PDF (μικρότερο
     μέγεθος repo).

Νέο στο 2.2:
  - Το manifest.csv έχει πλέον στήλη "downloaded_at" (ημερομηνία/ώρα λήψης).
  - Νέο όρισμα --refresh-after N: σελίδες που κατέβηκαν πριν από N ή
    περισσότερες ημέρες ξαναφκατεβαίνουν αυτόματα (ακόμα κι αν υπάρχουν ήδη),
    ώστε να πιάνει τυχόν αλλαγές περιεχομένου στο wiki με τον καιρό. Χωρίς
    αυτό το όρισμα, μια σελίδα που έχει κατέβει ΠΟΤΕ δεν ξαναφκατεβαίνει.
  - Μπορεί να μεταγλωττιστεί σε αυτόνομο Windows .exe (βλ. build_exe.ps1 /
    README, ενότητα "Build ως Windows .exe").

Νέο στο 2.3:
  - Το .exe πλέον ελέγχει μόνο του αν λείπει το Chromium του Playwright και,
    αν λείπει, το κατεβάζει/εγκαθιστά αυτόματα κατά την πρώτη εκτέλεση —
    ΧΩΡΙΣ να χρειάζεται καθόλου Python εγκατεστημένο στο μηχάνημα. Αρκεί
    σύνδεση internet. Ισχύει και όταν τρέχεις το .py απευθείας με python.

Εγκατάσταση για ανάπτυξη/τρέξιμο ως script (μία φορά):
    pip install -r requirements.txt
    playwright install chromium   # προαιρετικό πλέον — το κάνει μόνο του αν λείπει

Βασική χρήση:
    python entersoft_wiki_crawler_v2_3.py --insecure

Με login (αν χρειάζεται):
    python entersoft_wiki_crawler_v2_3.py --insecure --user MYUSER --password MYPASS

Αυτόματο refresh παλιών σελίδων μετά από 30 μέρες:
    python entersoft_wiki_crawler_v2_3.py --insecure --refresh-after 30

Χρήσιμα ορίσματα:
    --output-dir DIR       Ρίζα εξόδου (default: wiki_pdfs)
    --insecure              Παράκαμψη SSL verification (εταιρικό proxy)
    --user / --password     Login στο MediaWiki
    --delay SECONDS         Καθυστέρηση μεταξύ requests/σελίδων (default: 0.4)
    --dry-run               Μόνο λίστα κατηγοριών/σελίδων, χωρίς PDF
    --exclude REGEX         Regex για εξαίρεση ονομάτων κατηγοριών
                             (default εξαιρεί τυπικές maintenance categories)
    --min-category-size N   Αγνόησε κατηγορίες με λιγότερα από N μέλη (default 1)
    --refresh-after N       Ξαναφκατέβασε σελίδες παλαιότερες από N ημέρες
                             (default: καμία λήξη — ό,τι έχει κατέβει ποτέ
                             θεωρείται μόνιμα έτοιμο)
    --skip-chromium-check   Παράλειψε τον αυτόματο έλεγχο/εγκατάσταση Chromium
                             (χρήσιμο αν το έχεις ήδη εγκαταστήσει χειροκίνητα)
    --force                 Ξανακατέβασε ΟΛΕΣ τις σελίδες, αγνοώντας manifest.csv
                             και υπάρχοντα αρχεία (πλήρες overwrite).
                             Χωρίς αυτό: resume mode — κατεβάζει μόνο ό,τι
                             είναι νέο ή μπαγιάτικο σε σχέση με το manifest.csv.
"""

import argparse
import csv
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

# --- Fix για PyInstaller .exe: το bundled Playwright driver μπορεί να ψάξει
# το Chromium μέσα στον προσωρινό φάκελο εξαγωγής του .exe (_MEIxxxx), που
# διαγράφεται μόλις κλείσει το πρόγραμμα, αντί για το μόνιμο cache του χρήστη.
# Ορίζουμε ρητά το ίδιο, σταθερό path ώστε install & launch να συμφωνούν πάντα.
if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
    if sys.platform == "win32":
        _base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        _base = os.path.join(os.path.expanduser("~"), "Library", "Caches")
    else:
        _base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(_base, "ms-playwright")

import requests
from playwright.sync_api import sync_playwright

BASE = "https://wiki.entersoft.eu"
API = f"{BASE}/api.php"
INDEX = f"{BASE}/index.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EntersoftWikiCrawlerV2.3/2.3; personal use)"
}


# Τυπικά "άχρηστα" ονόματα κατηγοριών σε MediaWiki εγκαταστάσεις — προσαρμόσιμο με --exclude
DEFAULT_EXCLUDE = (
    r"(Pages with|Hidden|Χωρίς παραπομπές|Broken|Maintenance|Redirect"
    r"|Σελίδες με κατεστραμμένους συνδέσμους|Μη προσβάσιμες σελίδες)"
)


def make_session(user, password, insecure):
    s = requests.Session()
    s.headers.update(HEADERS)
    if insecure:
        s.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("[!] SSL certificate verification απενεργοποιημένη (--insecure).")

    if user and password:
        login_token = s.get(
            API,
            params={"action": "query", "meta": "tokens", "type": "login", "format": "json"},
        ).json()["query"]["tokens"]["logintoken"]

        resp = s.post(
            API,
            data={
                "action": "login",
                "lgname": user,
                "lgpassword": password,
                "lgtoken": login_token,
                "format": "json",
            },
        ).json()

        if resp.get("login", {}).get("result") != "Success":
            print(f"[!] Login απέτυχε: {resp}", file=sys.stderr)
        else:
            print("[+] Login επιτυχές.")
    return s


def get_all_categories(session, delay, min_size, exclude_re):
    """Επιστρέφει list of category names (χωρίς το πρόθεμα 'Κατηγορία:'/'Category:')."""
    categories = []
    params = {
        "action": "query",
        "list": "allcategories",
        "acprop": "size",
        "aclimit": "500",
        "format": "json",
    }
    while True:
        r = session.get(API, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        for cat in data.get("query", {}).get("allcategories", []):
            name = cat.get("*") or cat.get("category")
            size = cat.get("size", 0)
            if size < min_size:
                continue
            if exclude_re and re.search(exclude_re, name, re.IGNORECASE):
                continue
            categories.append(name)
        cont = data.get("continue")
        if not cont:
            break
        params.update(cont)
        time.sleep(delay)
    return categories


def get_category_members(session, category, delay):
    """Επιστρέφει list of (title, pageid) σελίδων (όχι αρχείων/υποκατηγοριών) μιας κατηγορίας."""
    members = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmtype": "page",
        "cmlimit": "500",
        "format": "json",
    }
    while True:
        r = session.get(API, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        for m in data.get("query", {}).get("categorymembers", []):
            members.append(m["title"])
        cont = data.get("continue")
        if not cont:
            break
        params.update(cont)
        time.sleep(delay)
    return members


def title_to_url(title):
    return f"{BASE}/wiki/{title.replace(' ', '_')}"


def sanitize_name(name):
    name = name.replace("_", " ").strip()
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name or "untitled"


def to_printable_url(url):
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}printable=yes"


def requests_cookies_to_playwright(session):
    domain = urlparse(BASE).netloc
    cookies = []
    for c in session.cookies:
        cookies.append({
            "name": c.name,
            "value": c.value,
            "domain": c.domain or domain,
            "path": c.path or "/",
        })
    return cookies


def load_previous_manifest(manifest_path):
    """
    Διαβάζει ένα manifest.csv από προηγούμενο run (αν υπάρχει) και επιστρέφει
    dict: title -> {"relative_path": ..., "downloaded_at": ... ή None},
    για κάθε σελίδα που είχε κατέβει επιτυχώς ('ok') ή ήταν ήδη γνωστή ως
    υπάρχουσα ('skipped-existing').
    """
    index = {}
    if not manifest_path.exists():
        return index
    try:
        with open(manifest_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("status") in ("ok", "skipped-existing") and row.get("relative_path"):
                    index[row["title"]] = {
                        "relative_path": row["relative_path"],
                        "downloaded_at": row.get("downloaded_at") or None,
                    }
    except Exception as e:
        print(f"[!] Δεν ήταν δυνατή η ανάγνωση προηγούμενου manifest.csv ({e}) — "
              f"θα ξεκινήσει σαν καθαρό run.", file=sys.stderr)
    return index


def is_stale(downloaded_at, refresh_after):
    """True αν το downloaded_at (ISO timestamp ή None) είναι παλαιότερο από refresh_after ημέρες."""
    if refresh_after is None:
        return False
    if not downloaded_at:
        return True  # άγνωστη ηλικία -> ασφαλέστερο να θεωρηθεί μπαγιάτικο
    try:
        dt = datetime.fromisoformat(downloaded_at)
    except ValueError:
        return True
    age_days = (datetime.now(timezone.utc) - dt).days
    return age_days >= refresh_after


def find_chromium_executable():
    """
    Ψάχνει χειροκίνητα το εγκατεστημένο (πλήρες, όχι headless-shell) Chromium
    μέσα στο PLAYWRIGHT_BROWSERS_PATH. Το κάνουμε αυτό γιατί μέσα σε
    PyInstaller .exe, το p.chromium.launch() έχει ένα γνωστό bug: ψάχνει
    πάντα σε λάθος, προσωρινό φάκελο (_MEIxxxx\\...\\.local-browsers), ό,τι
    και να ορίσουμε στο PLAYWRIGHT_BROWSERS_PATH. Εντοπίζοντας το εκτελέσιμο
    εμείς οι ίδιοι και περνώντας το ρητά στο launch(), παρακάμπτουμε τελείως
    αυτόν τον buggy αυτόματο εντοπισμό.
    """
    base = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""))
    if not base.exists():
        return None

    # πιάνει "chromium-1234" αλλά ΟΧΙ "chromium_headless_shell-1234"
    # (το headless-shell binary δεν υποστηρίζει page.pdf())
    candidates = sorted(
        (c for c in base.glob("chromium-*") if c.is_dir() and "headless_shell" not in c.name),
        reverse=True,
    )

    for c in candidates:
        if sys.platform == "win32":
            exe = c / "chrome-win64" / "chrome.exe"
        elif sys.platform == "darwin":
            exe = next(iter(c.glob("chrome-mac*/*.app/Contents/MacOS/*")), None)
        else:
            exe = c / "chrome-linux" / "chrome"
        if exe and Path(exe).exists():
            return str(exe)
    return None


def ensure_chromium_installed(skip_check=False):
    """
    Επιστρέφει το path του εγκατεστημένου Chromium executable (ή None αν
    παραλείφθηκε ο έλεγχος). Αν δεν βρεθεί, το κατεβάζει/εγκαθιστά αυτόματα
    καλώντας το ενσωματωμένο playwright CLI ΜΕΣΑ στην ίδια διεργασία
    (δουλεύει και μέσα σε PyInstaller .exe, χωρίς ξεχωριστό Python).
    """
    if skip_check:
        return None

    exe = find_chromium_executable()
    if exe:
        return exe

    print("[+] Το Chromium δεν βρέθηκε — γίνεται αυτόματη λήψη/εγκατάσταση "
          "(πρώτη εκτέλεση, ~150-300MB, χρειάζεται σύνδεση internet)...")
    try:
        from playwright.__main__ import main as playwright_cli_main
    except ImportError as e:
        print(f"[!] Δεν ήταν δυνατή η αυτόματη εγκατάσταση Chromium: {e}\n"
              f"    Τρέξε χειροκίνητα: playwright install chromium", file=sys.stderr)
        raise

    old_argv = sys.argv
    sys.argv = ["playwright", "install", "chromium"]
    try:
        playwright_cli_main()
    except SystemExit as e:
        if e.code not in (0, None):
            print(f"[!] Η εγκατάσταση Chromium απέτυχε (exit code {e.code}).", file=sys.stderr)
            raise
    finally:
        sys.argv = old_argv

    print("[+] Ολοκληρώθηκε η εγκατάσταση του Chromium.\n")

    exe = find_chromium_executable()
    if not exe:
        print("[!] Προειδοποίηση: δεν εντοπίστηκε το εκτελέσιμο Chromium μετά την "
              "εγκατάσταση — θα γίνει προσπάθεια με τον προεπιλεγμένο εντοπισμό "
              "του Playwright (ίσως αποτύχει μέσα σε .exe).", file=sys.stderr)
    return exe


def crawl(session, output_dir, delay, insecure, dry_run,
          exclude_re, min_category_size, force=False, refresh_after=None,
          skip_chromium_check=False):
    print("[+] Ανάκτηση λίστας κατηγοριών...")
    categories = get_all_categories(session, delay, min_category_size, exclude_re)
    print(f"[+] Βρέθηκαν {len(categories)} κατηγορίες (μετά τα φίλτρα).\n")

    # category -> [titles]
    cat_members = {}
    total_refs = 0
    for cat in categories:
        members = get_category_members(session, cat, delay)
        if members:
            cat_members[cat] = members
            total_refs += len(members)
        time.sleep(delay)

    unique_titles = {t for titles in cat_members.values() for t in titles}
    print(f"[+] {len(unique_titles)} μοναδικές σελίδες σε {len(cat_members)} μη-κενές κατηγορίες "
          f"({total_refs} αναφορές συνολικά).\n")

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.csv"

    previous = {} if force else load_previous_manifest(manifest_path)
    if previous:
        print(f"[+] Βρέθηκε προηγούμενο manifest.csv με {len(previous)} ήδη κατεβασμένες σελίδες.")
        if refresh_after is not None:
            stale = {t for t, info in previous.items() if is_stale(info["downloaded_at"], refresh_after)}
            print(f"[+] --refresh-after {refresh_after}: {len(stale)} από αυτές θεωρούνται μπαγιάτικες "
                  f"και θα ξαναφκατεβούν.")
        already = unique_titles & previous.keys()
        new_count = len(unique_titles) - len(already)
        print(f"[+] {len(already)} υπάρχουν ήδη στο manifest · {new_count} είναι εντελώς νέες/λείπουν.\n")

    rendered = {}        # title -> relative path (πρώτη κατηγορία που το κατέβασε σε αυτό το run)
    used_paths = set()   # dest paths ήδη χρησιμοποιημένα ΣΕ ΑΥΤΟ ΤΟ run (για γνήσιες συγκρούσεις ονομάτων)
    ok, failed, dup, skipped, refreshed = 0, 0, 0, 0, 0

    with open(manifest_path, "w", newline="", encoding="utf-8") as mf:
        writer = csv.writer(mf)
        writer.writerow(["category", "title", "url", "relative_path", "status", "downloaded_at"])

        if dry_run:
            for cat, titles in cat_members.items():
                for title in titles:
                    if title in previous:
                        stale = is_stale(previous[title]["downloaded_at"], refresh_after)
                        status = "dry-run (stale, would refresh)" if stale else "dry-run (would skip, already have it)"
                        rel = previous[title]["relative_path"]
                    else:
                        status = "dry-run (new)"
                        rel = ""
                    writer.writerow([cat, title, title_to_url(title), rel, status, ""])
            print("[dry-run] Δεν παράχθηκαν PDF. Δες το manifest.csv για την πλήρη λίστα.")
            return

        chromium_exe = ensure_chromium_installed(skip_check=skip_chromium_check)

        with sync_playwright() as p:
            launch_kwargs = {"executable_path": chromium_exe} if chromium_exe else {}
            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(ignore_https_errors=insecure)
            cookies = requests_cookies_to_playwright(session)
            if cookies:
                context.add_cookies(cookies)
            page = context.new_page()

            for cat, titles in cat_members.items():
                cat_dir = output_dir / sanitize_name(cat)

                for title in titles:
                    url = title_to_url(title)

                    if title in rendered:
                        # ήδη κατέβηκε από άλλη κατηγορία (σε αυτό το run) -> μόνο αναφορά
                        rel_path, dl_at = rendered[title]
                        writer.writerow([cat, title, url, rel_path, "duplicate-ref", dl_at])
                        dup += 1
                        continue

                    # --- resume mode: το manifest από προηγούμενο run λέει ότι το έχουμε ήδη ---
                    if title in previous:
                        prev_info = previous[title]
                        prev_path = output_dir / prev_info["relative_path"]
                        stale = is_stale(prev_info["downloaded_at"], refresh_after)

                        if prev_path.exists() and not stale:
                            rel_path = prev_info["relative_path"]
                            rendered[title] = (rel_path, prev_info["downloaded_at"] or "")
                            used_paths.add(prev_path)
                            writer.writerow([cat, title, url, rel_path, "skipped-existing",
                                              prev_info["downloaded_at"] or ""])
                            skipped += 1
                            continue
                        elif stale:
                            print(f"[~] '{title}' έχει μπαγιατέψει (> {refresh_after} ημέρες) — ανανεώνεται.")
                            refreshed += 1
                        else:
                            # το manifest το ήξερε, αλλά το αρχείο λείπει (π.χ. σβήστηκε) -> ξανακατέβασέ το
                            print(f"[!] '{title}' ήταν στο manifest αλλά λείπει το αρχείο — ξανακατεβαίνει.",
                                  file=sys.stderr)

                    cat_dir.mkdir(parents=True, exist_ok=True)
                    filename = sanitize_name(title) + ".pdf"
                    dest = cat_dir / filename

                    if dest in used_paths:
                        # γνήσια σύγκρουση ονόματος ΜΕΣΑ σε αυτό το run (2 διαφορετικοί τίτλοι -> ίδιο filename)
                        counter = 1
                        base_dest = dest
                        while dest in used_paths:
                            dest = cat_dir / f"{base_dest.stem}_{counter}{base_dest.suffix}"
                            counter += 1
                    elif dest.exists() and not force and title not in previous:
                        # υπάρχει στο δίσκο αλλά δεν ήταν στο manifest (π.χ. χειροκίνητο αρχείο) -> resume ούτως ή άλλως
                        rel_path = str(dest.relative_to(output_dir))
                        rendered[title] = (rel_path, "")
                        used_paths.add(dest)
                        writer.writerow([cat, title, url, rel_path, "skipped-existing", ""])
                        skipped += 1
                        continue

                    used_paths.add(dest)

                    try:
                        page.goto(to_printable_url(url), wait_until="networkidle", timeout=30000)
                        page.pdf(path=str(dest), format="A4", print_background=True,
                                 margin={"top": "15mm", "bottom": "15mm",
                                         "left": "12mm", "right": "12mm"})
                        rel_path = str(dest.relative_to(output_dir))
                        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
                        rendered[title] = (rel_path, now_iso)
                        print(f"[+] {rel_path}")
                        writer.writerow([cat, title, url, rel_path, "ok", now_iso])
                        ok += 1
                    except Exception as e:
                        print(f"[!] Αποτυχία στο '{title}' ({url}): {e}", file=sys.stderr)
                        writer.writerow([cat, title, url, "", f"failed: {e}", ""])
                        failed += 1

                    time.sleep(delay)

            browser.close()

    print(f"\n[+] Ολοκληρώθηκε. Νέα PDF: {ok} (εκ των οποίων {refreshed} ανανεώσεις) "
          f"| Παραλείφθηκαν (ήδη υπήρχαν): {skipped} "
          f"| Διπλότυπες αναφορές: {dup} | Αποτυχίες: {failed}")
    print(f"[+] Έξοδος στο: {output_dir.resolve()}")
    print(f"[+] Manifest: {manifest_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="ES-Crawler v2.3 — Αυτόματη λήψη όλων των σελίδων του Entersoft wiki ως PDF, "
                    "ανά κατηγορία, με resume μέσω manifest.csv, auto-refresh παλιών σελίδων, "
                    "και αυτόματη εγκατάσταση Chromium"
    )
    parser.add_argument("--output-dir", default="wiki_pdfs")
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--exclude", default=DEFAULT_EXCLUDE,
                         help="Regex ονομάτων κατηγοριών προς εξαίρεση")
    parser.add_argument("--min-category-size", type=int, default=1)
    parser.add_argument("--refresh-after", type=int, default=None,
                         help="Ξαναφκατέβασε σελίδες παλαιότερες από N ημέρες (default: ποτέ)")
    parser.add_argument("--skip-chromium-check", action="store_true",
                         help="Παράλειψε τον αυτόματο έλεγχο/εγκατάσταση Chromium")
    parser.add_argument("--force", action="store_true",
                         help="Ξανακατέβασε (overwrite) όλες τις σελίδες, αγνοώντας το manifest.csv "
                              "και τα υπάρχοντα αρχεία. Χωρίς αυτό: resume mode (default).")
    args = parser.parse_args()

    session = make_session(args.user, args.password, args.insecure)
    crawl(
        session,
        Path(args.output_dir),
        args.delay,
        args.insecure,
        args.dry_run,
        args.exclude,
        args.min_category_size,
        force=args.force,
        refresh_after=args.refresh_after,
        skip_chromium_check=args.skip_chromium_check,
    )


if __name__ == "__main__":
    main()
