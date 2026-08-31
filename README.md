# ES-Crawler v2.3

Αυτόματη λήψη όλων των σελίδων του [wiki.entersoft.eu](https://wiki.entersoft.eu)
ως PDF, οργανωμένες σε φακέλους ανά κατηγορία (MediaWiki category).

Δεν χρειάζεται να δηλώνεις χειροκίνητα κάθε κατηγορία — το script τις
ανακαλύπτει αυτόματα μέσω του MediaWiki API και κατεβάζει όλες τις σελίδες
που ανήκουν σε κάθε μία, ρεντάροντας κάθε σελίδα σε πλήρες, αναγνώσιμο PDF
μέσω headless Chromium (Playwright) — ακριβώς σαν Ctrl+P → Save as PDF.

Αν μια σελίδα ανήκει σε πολλές κατηγορίες, αποθηκεύεται **μία φορά** (στην
πρώτη κατηγορία που τη συναντάει)· στις υπόλοιπες καταγράφεται μόνο αναφορά
στο manifest — έτσι δεν υπάρχουν διπλότυπα PDF και το μέγεθος μένει μικρό.

## Εγκατάσταση

```powershell
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

## Χρήση

```powershell
python entersoft_wiki_crawler_v2_3.py --insecure
```

Το `--insecure` παρακάμπτει την επαλήθευση SSL certificate — χρήσιμο αν
βρίσκεσαι πίσω από εταιρικό proxy που κάνει SSL inspection.

Με login (αν κάποιες σελίδες το απαιτούν):

```powershell
python entersoft_wiki_crawler_v2_3.py --insecure --user MYUSER --password MYPASS
```

Δοκιμή χωρίς να παραχθούν PDF (μόνο λίστα κατηγοριών/σελίδων στο manifest):

```powershell
python entersoft_wiki_crawler_v2_3.py --insecure --dry-run
```

Αυτόματο refresh σελίδων που έχουν κατέβει πριν από 30+ μέρες:

```powershell
python entersoft_wiki_crawler_v2_3.py --insecure --refresh-after 30
```

### Χρήσιμα ορίσματα

| Όρισμα | Περιγραφή | Default |
|---|---|---|
| `--output-dir DIR` | Ρίζα εξόδου | `wiki_pdfs` |
| `--delay SECONDS` | Καθυστέρηση μεταξύ requests/σελίδων | `0.4` |
| `--exclude REGEX` | Regex για εξαίρεση ονομάτων κατηγοριών | βλ. `DEFAULT_EXCLUDE` στο script |
| `--min-category-size N` | Αγνόησε κατηγορίες με λιγότερα από N μέλη | `1` |
| `--refresh-after N` | Ξαναφκατέβασε σελίδες παλαιότερες από N ημέρες | καμία λήξη |
| `--dry-run` | Μόνο λίστα, χωρίς παραγωγή PDF | off |
| `--force` | Ξανακατέβασε (overwrite) ΟΛΕΣ τις σελίδες, αγνοώντας manifest/δίσκο | off |

### Resume mode & αυτόματο refresh (νέο στο 2.2)

Αν ξανατρέξεις το script στον ίδιο `--output-dir`, διαβάζει το `manifest.csv`
από το προηγούμενο run και **δεν** ξαναδιαβάζει σελίδες που είχαν κατέβει
επιτυχώς — τις παραλείπει (`skipped-existing`) και κατεβάζει ουσιαστικά μόνο
ό,τι είναι καινούριο (π.χ. νέες σελίδες που προστέθηκαν στο wiki).

Το manifest πλέον κρατάει και **πότε** κατέβηκε κάθε σελίδα (στήλη
`downloaded_at`). Με `--refresh-after N`, σελίδες παλαιότερες από N ημέρες
θεωρούνται "μπαγιάτικες" και ξαναφκατεβαίνουν αυτόματα, ώστε να πιάνεις
τυχόν αλλαγές περιεχομένου στο wiki με τον καιρό — χωρίς αυτό το όρισμα, μια
σελίδα που κατέβηκε ποτέ θεωρείται μόνιμα έτοιμη.

Αν κάποιο PDF λείπει από τον δίσκο ενώ το manifest το είχε ως έτοιμο (π.χ.
το έσβησες χειροκίνητα), το ξανακατεβάζει αυτόματα (self-heal). Για πλήρες
ξαναδιάβασμα όλων (αγνοώντας manifest και υπάρχοντα αρχεία), χρησιμοποίησε
`--force`.

## Έξοδος

```
wiki_pdfs/
  ERP/
    EBS-IntroEL.pdf
    ...
  CRM/
    CRM_MarketingPromotionPrograms_EN.pdf
    ...
  manifest.csv
```

Το `manifest.csv` καταγράφει για κάθε σελίδα: κατηγορία, τίτλο, URL, το
σχετικό path του PDF, το status (`ok` / `skipped-existing` / `duplicate-ref`
/ `failed: ...`), και πότε κατέβηκε (`downloaded_at`, UTC ISO-8601).

## Build ως Windows .exe (αυτόνομο, χωρίς εγκατεστημένο Python)

```powershell
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

.\build_exe.ps1
```

Το εκτελέσιμο θα βρίσκεται στο `dist\entersoft_wiki_crawler_v2_3.exe` και
τρέχει με τα ίδια ακριβώς ορίσματα:

```powershell
dist\entersoft_wiki_crawler_v2_3.exe --insecure
```

**Νέο στο 2.3:** το `.exe` **δεν** χρειάζεται πια χειροκίνητο
`playwright install chromium`. Στην πρώτη εκτέλεση σε ένα μηχάνημα, αν δεν
βρει το Chromium, το κατεβάζει/εγκαθιστά μόνο του (χρειάζεται μόνο σύνδεση
internet — καθόλου Python). Αν θες να το παραλείψεις (π.χ. το έχεις ήδη
εγκαταστήσει), χρησιμοποίησε `--skip-chromium-check`.

## Σημειώσεις

- Τα παραγόμενα PDF, το `.venv/`, και το build output (`build/`, `dist/`,
  `*.spec`) **δεν** μπαίνουν στο git repo (βλ. `.gitignore`) — παράγονται
  ξανά τρέχοντας το script/build. Αυτό κρατάει το repo μικρό.
- Αν το δίκτυο κάνει SSL interception (π.χ. εταιρικό proxy) και δεις σφάλμα
  `CERTIFICATE_VERIFY_FAILED`, χρησιμοποίησε το `--insecure`.
