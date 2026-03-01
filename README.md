# 🎬 Drehbuch → Storyboard MP4

Konvertiert ein Drehbuch im Standard-Screenwriting-Format automatisch in ein animiertes **Storyboard-Video (MP4)** – komplett lokal, ohne externe APIs.

Jede Szene wird als Storyboard-Karte dargestellt mit:
- Szenennummer, Kopf und Regieanweisung
- Dialog der Figuren
- Fertig formuliertem **Image Prompt** für Midjourney, Stable Diffusion oder DALL-E

---

## 📦 Installation

```bash
git clone https://github.com/DEIN-USERNAME/drehbuch-storyboard.git
cd drehbuch-storyboard
pip install -r requirements.txt
```

---

## 🚀 Verwendung

### Demo (Mephisto-Beispiel)
```bash
python3 drehbuch_zu_storyboard.py --demo
```

### Eigenes Drehbuch
```bash
python3 drehbuch_zu_storyboard.py mein_film.txt
```

### Mit Optionen
```bash
python3 drehbuch_zu_storyboard.py mein_film.txt --ausgabe storyboard.mp4 --dauer 10
```

| Option | Standard | Beschreibung |
|--------|----------|--------------|
| `--ausgabe` / `-o` | `storyboard.mp4` | Name der Ausgabedatei |
| `--dauer` / `-d` | `8` | Sekunden pro Szene |
| `--demo` | – | Erstellt Demo-Drehbuch (Mephisto) |

---

## 📝 Drehbuch-Format

Das Programm versteht das Standard-Screenwriting-Format:

```
INT. WOHNZIMMER - NACHT

Die Kamera schwenkt langsam durch den dunklen Raum.
Ein einsames Licht brennt in der Ecke.

        ANNA
  Ich wusste, dass du kommen würdest.

        MAX
  Ich hatte keine Wahl.

EXT. BERLINER STRASSE - MORGEN

Herbstblätter wehen über das nasse Pflaster.
...
```

**Szenenkopf-Formate (werden automatisch erkannt):**
- `INT. ORT - TAGESZEIT`
- `EXT. ORT - TAGESZEIT`
- `INT/EXT. ORT - TAGESZEIT`
- `INNEN ORT - TAGESZEIT`
- `AUSSEN ORT - TAGESZEIT`

---

## 🎨 Workflow

```
Drehbuch.txt
     │
     ▼
drehbuch_zu_storyboard.py
     │
     ▼
storyboard.mp4 (mit Image-Prompts)
     │
     ▼
Prompts kopieren → Midjourney / Stable Diffusion / DALL-E
     │
     ▼
Bilder im Video ersetzen → Fertig!
```

---

## 🖼️ Screenshot

Jede Storyboard-Karte enthält:

```
┌─────────────────────────────┬──────────────────────────┐
│ SZENE 01 / 04               │ 🎨 IMAGE PROMPT          │
│ INT. BERLINER THEATER - NACHT│                          │
│                             │ Scene at berliner theater │
│ Regieanweisung...           │ night, moonlight,         │
│                             │ cinematic film still...   │
│ [ KI-Bild hier einfügen ]   │                          │
├─────────────────────────────│ EMPFOHLENE ZUSÄTZE:       │
│ DIALOG                      │ • --ar 16:9 --v 6        │
│ HENDRIK: Ich bin der...     │ • cinematic, 8K           │
└─────────────────────────────┴──────────────────────────┘
```

---

## 📋 Anforderungen

- Python 3.10+
- Pillow
- MoviePy

---

## 💡 Tipps

- **Szenenanzahl:** Funktioniert mit beliebig vielen Szenen
- **Sprache:** Prompts werden automatisch auf Englisch optimiert (ideal für KI-Tools)
- **Stimmung:** Schlüsselwörter in der Regieanweisung (dunkel, hell, ruhig, bedrohlich...) fließen automatisch in den Prompt ein
- **Eigene Schriften:** Systemschriften werden automatisch erkannt (DejaVu, Liberation)

---

## 📄 Lizenz

MIT License – frei verwendbar für Bildung und eigene Projekte.

---

*Entwickelt für den Einsatz im Deutschunterricht an der Kantonsschule Ausserschwyz (KSA)*
