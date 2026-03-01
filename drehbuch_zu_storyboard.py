#!/usr/bin/env python3
"""
Drehbuch → Animiertes Storyboard MP4
=====================================
Liest ein Drehbuch (Textdatei) ein, parst Szenen,
generiert Storyboard-Karten mit Image-Prompts und
exportiert ein MP4-Video.

Verwendung:
    python3 drehbuch_zu_storyboard.py mein_drehbuch.txt
    python3 drehbuch_zu_storyboard.py mein_drehbuch.txt --dauer 6 --ausgabe film.mp4
"""

import re
import sys
import os
import textwrap
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ─── Konfiguration ────────────────────────────────────────────────────────────

BREITE = 1280
HOEHE  = 720

# Farben (Dunkelfilm-Ästhetik)
FARBE_HINTERGRUND  = (15, 15, 25)
FARBE_PANEL        = (25, 25, 40)
FARBE_AKZENT       = (255, 160, 30)     # Gold
FARBE_SZENE_BG     = (30, 30, 50)
FARBE_TEXT_HAUPT   = (240, 240, 240)
FARBE_TEXT_GRAU    = (160, 160, 180)
FARBE_PROMPT_BG    = (20, 40, 30)
FARBE_PROMPT_TEXT  = (100, 220, 130)
FARBE_DIALOG_BG    = (40, 25, 25)
FARBE_DIALOG_TEXT  = (220, 180, 140)

# ─── Schriftarten ─────────────────────────────────────────────────────────────

def lade_schrift(groesse, fett=False):
    """Lädt eine Systemschrift, Fallback auf PIL-Standard."""
    kandidaten_fett = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    kandidaten_normal = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for pfad in (kandidaten_fett if fett else kandidaten_normal):
        if os.path.exists(pfad):
            return ImageFont.truetype(pfad, groesse)
    return ImageFont.load_default()


# ─── Drehbuch-Parser ──────────────────────────────────────────────────────────

def parse_drehbuch(text: str) -> list[dict]:
    """
    Parst ein Drehbuch im Standard-Format:
      - Szenenkopf: INT. / EXT. (Großbuchstaben, beginnt eine neue Szene)
      - Regieanweisung: normaler Text
      - Figur: GROSSBUCHSTABEN (vor Dialog)
      - Dialog: eingerückter Text nach Figur
    """
    zeilen = text.splitlines()
    szenen = []
    aktuelle_szene = None

    SZENENKOPF = re.compile(r'^(INT\.|EXT\.|INT/EXT\.|INNEN|AUSSEN|I/A)\s+', re.IGNORECASE)
    FIGUR       = re.compile(r'^[ \t]{2,}([A-ZÄÖÜ][A-ZÄÖÜ\s\-\.]{1,30})$')
    DIALOG_ZEILE= re.compile(r'^[ \t]{4,}(.+)$')
    LEER        = re.compile(r'^\s*$')

    modus = None  # 'regie', 'figur', 'dialog'
    letzter_figur = ""

    for zeile in zeilen:
        if SZENENKOPF.match(zeile.strip()):
            if aktuelle_szene:
                szenen.append(aktuelle_szene)
            aktuelle_szene = {
                "nummer":    len(szenen) + 1,
                "kopf":      zeile.strip(),
                "regie":     [],
                "dialoge":   [],  # Liste von (figur, text)
            }
            modus = None
            continue

        if aktuelle_szene is None:
            # Text vor erster Szene = Titel etc.
            continue

        stripped = zeile.strip()
        if LEER.match(zeile):
            modus = None
            continue

        # Figur (mind. 2 Leerzeichen Einzug, Großbuchstaben)
        m = FIGUR.match(zeile)
        if m and modus != 'dialog':
            letzter_figur = m.group(1).strip()
            modus = 'figur'
            continue

        # Dialog (mind. 4 Leerzeichen oder nach Figur)
        m = DIALOG_ZEILE.match(zeile)
        if m and modus in ('figur', 'dialog'):
            if modus == 'figur':
                # Neue Dialog-Einheit
                aktuelle_szene["dialoge"].append({"figur": letzter_figur, "text": m.group(1)})
                modus = 'dialog'
            else:
                # Fortsetzung Dialog
                aktuelle_szene["dialoge"][-1]["text"] += " " + m.group(1)
            continue

        # Regieanweisung
        if stripped:
            aktuelle_szene["regie"].append(stripped)
            modus = 'regie'

    if aktuelle_szene:
        szenen.append(aktuelle_szene)

    return szenen


# ─── Prompt-Generator ─────────────────────────────────────────────────────────

def generiere_prompt(szene: dict) -> str:
    """Erzeugt einen englischen Image-Prompt aus den Szenendaten."""
    kopf = szene["kopf"].lower()

    # Ort und Zeit aus dem Szenenkopf
    ort_zeit = szene["kopf"].replace("INT.", "").replace("EXT.", "").replace("INNEN", "").replace("AUSSEN", "").strip()
    teile = [t.strip() for t in ort_zeit.split("-")]
    ort  = teile[0] if teile else "location"
    zeit = teile[1] if len(teile) > 1 else ""

    # Innen/Außen
    licht = "indoor lighting" if any(w in kopf for w in ["int", "innen"]) else "natural outdoor lighting"

    # Tageszeit
    tageszeit_map = {
        "nacht": "night, moonlight, artificial lights",
        "tag":   "daylight, bright sun",
        "morgen":"golden hour, morning mist",
        "abend": "sunset, golden orange sky",
        "dawn":  "dawn, soft pink sky",
    }
    tageszeit_str = ""
    for key, val in tageszeit_map.items():
        if key in (zeit + kopf).lower():
            tageszeit_str = val
            break

    # Stimmung aus Regieanweisungen
    regie_text = " ".join(szene["regie"][:3])
    stimmung = ""
    stimmungs_map = {
        "dunkel":     "dark, moody atmosphere",
        "hell":       "bright, cheerful atmosphere",
        "einsam":     "lonely, isolated",
        "bedrohlich": "threatening, tense atmosphere",
        "romantisch": "romantic, warm tones",
        "ruhig":      "calm, peaceful",
        "chaotisch":  "chaotic, dynamic",
    }
    for key, val in stimmungs_map.items():
        if key in regie_text.lower():
            stimmung = val
            break

    # Figuren
    figuren = list(dict.fromkeys([d["figur"] for d in szene["dialoge"]]))[:3]
    figuren_str = f"featuring characters: {', '.join(figuren)}" if figuren else ""

    # Stil
    stil = "cinematic film still, 35mm photography, shallow depth of field, professional cinematography"

    prompt_teile = [
        f"Scene at {ort}",
        tageszeit_str,
        licht,
        stimmung,
        figuren_str,
        regie_text[:120] if regie_text else "",
        stil,
    ]
    prompt = ", ".join(p for p in prompt_teile if p.strip())
    return prompt


# ─── Storyboard-Karte zeichnen ────────────────────────────────────────────────

def zeichne_karte(szene: dict, gesamt: int) -> np.ndarray:
    """Erstellt eine 1280×720 Storyboard-Karte als numpy-Array (RGB)."""
    img = Image.new("RGB", (BREITE, HOEHE), FARBE_HINTERGRUND)
    d   = ImageDraw.Draw(img)

    # Schriften
    f_gross   = lade_schrift(28, fett=True)
    f_mittel  = lade_schrift(20)
    f_klein   = lade_schrift(16)
    f_mikro   = lade_schrift(14)

    # ── Linke Spalte: Szenen-Panel ──────────────────────────────────────────

    panel_x, panel_y = 30, 30
    panel_b, panel_h = 580, 350

    # Hintergrund Panel (Bild-Placeholder)
    d.rounded_rectangle(
        [panel_x, panel_y, panel_x + panel_b, panel_y + panel_h],
        radius=12, fill=FARBE_PANEL, outline=FARBE_AKZENT, width=2
    )

    # Szenennummer
    nr_text = f"SZENE {szene['nummer']:02d} / {gesamt:02d}"
    d.text((panel_x + 16, panel_y + 12), nr_text, font=f_gross, fill=FARBE_AKZENT)

    # Szenenkopf
    kopf_y = panel_y + 55
    for linie in textwrap.wrap(szene["kopf"], 45):
        d.text((panel_x + 16, kopf_y), linie, font=f_mittel, fill=FARBE_TEXT_HAUPT)
        kopf_y += 26

    # Regie-Beschreibung
    regie_y = kopf_y + 12
    d.text((panel_x + 16, regie_y - 4), "REGIEANWEISUNG", font=f_mikro, fill=FARBE_TEXT_GRAU)
    regie_y += 18
    regie_voll = " ".join(szene["regie"])
    for linie in textwrap.wrap(regie_voll, 52)[:6]:
        d.text((panel_x + 16, regie_y), linie, font=f_klein, fill=FARBE_TEXT_HAUPT)
        regie_y += 22

    # Kamera-Icon Placeholder
    cam_cx, cam_cy = panel_x + panel_b // 2, panel_y + panel_h - 55
    d.ellipse([cam_cx-30, cam_cy-20, cam_cx+30, cam_cy+20], outline=FARBE_AKZENT, width=2)
    d.text((cam_cx - 60, cam_cy + 28), "[ Hier: KI-generiertes Bild einfügen ]",
           font=f_mikro, fill=FARBE_TEXT_GRAU)

    # ── Linke Spalte: Dialog-Panel ───────────────────────────────────────────

    diag_y = panel_y + panel_h + 16
    diag_h = HOEHE - diag_y - 30

    d.rounded_rectangle(
        [panel_x, diag_y, panel_x + panel_b, diag_y + diag_h],
        radius=10, fill=FARBE_DIALOG_BG, outline=(80, 50, 50), width=1
    )
    d.text((panel_x + 16, diag_y + 10), "DIALOG", font=f_mikro, fill=FARBE_TEXT_GRAU)

    dy = diag_y + 30
    for dial in szene["dialoge"][:3]:
        if dy + 40 > diag_y + diag_h:
            break
        d.text((panel_x + 16, dy), dial["figur"] + ":", font=f_klein, fill=FARBE_AKZENT)
        dy += 20
        for linie in textwrap.wrap(dial["text"], 52)[:2]:
            d.text((panel_x + 28, dy), linie, font=f_mikro, fill=FARBE_DIALOG_TEXT)
            dy += 18
        dy += 6

    if not szene["dialoge"]:
        d.text((panel_x + 16, diag_y + 30), "— kein Dialog —",
               font=f_klein, fill=FARBE_TEXT_GRAU)

    # ── Rechte Spalte: Prompt ────────────────────────────────────────────────

    pr_x  = panel_x + panel_b + 20
    pr_b  = BREITE - pr_x - 30
    pr_y  = 30
    pr_h  = HOEHE - 60

    d.rounded_rectangle(
        [pr_x, pr_y, pr_x + pr_b, pr_y + pr_h],
        radius=12, fill=FARBE_PROMPT_BG, outline=(50, 120, 70), width=2
    )

    d.text((pr_x + 16, pr_y + 14), "🎨  IMAGE PROMPT", font=f_gross, fill=FARBE_PROMPT_TEXT)
    d.text((pr_x + 16, pr_y + 46), "Für: Midjourney · Stable Diffusion · DALL-E",
           font=f_mikro, fill=FARBE_TEXT_GRAU)

    # Trennlinie
    d.line([(pr_x + 16, pr_y + 68), (pr_x + pr_b - 16, pr_y + 68)],
           fill=(50, 100, 60), width=1)

    prompt = generiere_prompt(szene)
    py = pr_y + 82
    for linie in textwrap.wrap(prompt, 36):
        d.text((pr_x + 16, py), linie, font=f_mittel, fill=FARBE_PROMPT_TEXT)
        py += 28

    # Stil-Vorschläge
    py += 20
    d.line([(pr_x + 16, py), (pr_x + pr_b - 16, py)], fill=(50, 100, 60), width=1)
    py += 12
    d.text((pr_x + 16, py), "EMPFOHLENE ZUSÄTZE:", font=f_mikro, fill=FARBE_TEXT_GRAU)
    py += 20
    extras = [
        "--ar 16:9  --v 6",
        "cinematic, 8K, film grain",
        "hyperrealistic, award-winning",
        "color grading: teal & orange",
    ]
    for ex in extras:
        d.text((pr_x + 20, py), f"• {ex}", font=f_mikro, fill=(120, 180, 140))
        py += 20

    # Figuren-Liste
    figuren = list(dict.fromkeys([dl["figur"] for dl in szene["dialoge"]]))
    if figuren:
        py += 12
        d.line([(pr_x + 16, py), (pr_x + pr_b - 16, py)], fill=(50, 100, 60), width=1)
        py += 12
        d.text((pr_x + 16, py), "FIGUREN IN DIESER SZENE:", font=f_mikro, fill=FARBE_TEXT_GRAU)
        py += 20
        for fig in figuren[:5]:
            d.text((pr_x + 20, py), f"→ {fig}", font=f_klein, fill=FARBE_TEXT_HAUPT)
            py += 22

    return np.array(img)


# ─── Titelkarte ───────────────────────────────────────────────────────────────

def zeichne_titel(titel: str, anzahl_szenen: int) -> np.ndarray:
    img = Image.new("RGB", (BREITE, HOEHE), (8, 8, 15))
    d   = ImageDraw.Draw(img)
    f_xl    = lade_schrift(54, fett=True)
    f_gross = lade_schrift(28)
    f_mittel= lade_schrift(20)
    f_klein = lade_schrift(16)

    # Goldene Rahmenlinie
    d.rectangle([20, 20, BREITE-20, HOEHE-20], outline=FARBE_AKZENT, width=2)
    d.rectangle([28, 28, BREITE-28, HOEHE-28], outline=(100, 80, 20), width=1)

    # Zentrierter Titel
    bbox = d.textbbox((0, 0), titel, font=f_xl)
    tw   = bbox[2] - bbox[0]
    d.text(((BREITE - tw) // 2, 200), titel, font=f_xl, fill=FARBE_AKZENT)

    # Untertitel
    sub = "Automatisch generiertes Storyboard"
    bbox2 = d.textbbox((0, 0), sub, font=f_gross)
    d.text(((BREITE - (bbox2[2]-bbox2[0])) // 2, 290), sub, font=f_gross, fill=FARBE_TEXT_GRAU)

    # Info
    info = f"{anzahl_szenen} Szenen  •  Prompts für Midjourney / Stable Diffusion / DALL-E"
    bbox3 = d.textbbox((0, 0), info, font=f_mittel)
    d.text(((BREITE - (bbox3[2]-bbox3[0])) // 2, 380), info, font=f_mittel, fill=FARBE_TEXT_HAUPT)

    # Anleitung
    anl_y = 470
    anleitungen = [
        "① Kopiere den Image Prompt aus jeder Szene",
        "② Füge ihn in Midjourney, DALL-E oder Stable Diffusion ein",
        "③ Ersetze die Platzhalter durch deine generierten Bilder",
    ]
    for a in anleitungen:
        bbox4 = d.textbbox((0, 0), a, font=f_klein)
        d.text(((BREITE - (bbox4[2]-bbox4[0])) // 2, anl_y), a, font=f_klein, fill=(180, 180, 200))
        anl_y += 30

    return np.array(img)


def zeichne_abschluss() -> np.ndarray:
    img = Image.new("RGB", (BREITE, HOEHE), (8, 8, 15))
    d   = ImageDraw.Draw(img)
    f   = lade_schrift(36, fett=True)
    f2  = lade_schrift(20)
    d.rectangle([20, 20, BREITE-20, HOEHE-20], outline=FARBE_AKZENT, width=2)
    text = "STORYBOARD ABGESCHLOSSEN"
    bbox = d.textbbox((0, 0), text, font=f)
    d.text(((BREITE-(bbox[2]-bbox[0]))//2, 280), text, font=f, fill=FARBE_AKZENT)
    sub = "Jetzt Bilder mit KI generieren und einfügen!"
    bbox2 = d.textbbox((0, 0), sub, font=f2)
    d.text(((BREITE-(bbox2[2]-bbox2[0]))//2, 350), sub, font=f2, fill=FARBE_TEXT_GRAU)
    return np.array(img)


# ─── MP4-Export ───────────────────────────────────────────────────────────────

def exportiere_mp4(frames: list[np.ndarray], ausgabe: str, fps: float, dauer_pro_frame: float):
    """Erstellt MP4 aus Frame-Liste."""
    try:
        from moviepy import ImageClip, concatenate_videoclips
    except ImportError:
        from moviepy.editor import ImageClip, concatenate_videoclips

    clips = []
    for frame in frames:
        clip = ImageClip(frame, duration=dauer_pro_frame)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")
    video.write_videofile(ausgabe, fps=fps, codec="libx264",
                          audio=False, logger=None)
    print(f"✅  MP4 gespeichert: {ausgabe}")


# ─── Hauptprogramm ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Drehbuch → Storyboard MP4"
    )
    parser.add_argument("drehbuch", nargs="?",
                        help="Pfad zur Drehbuch-Textdatei (.txt)")
    parser.add_argument("--ausgabe", "-o", default="storyboard.mp4",
                        help="Ausgabe-Dateiname (Standard: storyboard.mp4)")
    parser.add_argument("--dauer", "-d", type=float, default=8.0,
                        help="Sekunden pro Szene (Standard: 8)")
    parser.add_argument("--demo", action="store_true",
                        help="Erstellt ein Demo-Drehbuch und verarbeitet es")
    args = parser.parse_args()

    # Demo-Modus
    if args.demo or not args.drehbuch:
        print("🎬  Demo-Modus: Erstelle Beispiel-Drehbuch...")
        demo_text = """MEPHISTO
Ein Drehbuch nach Klaus Mann

INT. BERLINER THEATER - NACHT

Die große Bühne liegt im Halbdunkel. Scheinwerfer beleuchten einzelne Requisiten.
HENDRIK HÖFGEN tritt auf, gekleidet als Mephisto. Er wirkt bedrohlich und charismatisch.
Die Kulissen werfen lange Schatten auf den Boden.

        HENDRIK
  Ich bin der Geist, der stets verneint!
  Und das mit Recht – denn alles, was entsteht,
  ist wert, dass es zugrunde geht.

        NICOLETTA
  Hendrik – du bist grandios. Du bist... ein anderer Mensch.

INT. DIREKTORENBÜRO - TAG

Ein prachtvolles Büro. NS-Fahnen schmücken die Wände.
HENDRIK steht vor dem GENERALINTENDANTEN. Er wirkt nervös, lächelt aber unterwürfig.
Sonnenlicht fällt durch hohe Fenster.

        GENERALINTENDANT
  Sie haben eine große Karriere vor sich, Höfgen.
  Vorausgesetzt, Sie bleiben... loyal.

        HENDRIK
  Selbstverständlich, Exzellenz.
  Die Kunst dient dem Volk.

EXT. BERLINER STRASSE - MORGEN

Eine graue Stadtlandschaft. Menschen in Mänteln eilen vorbei.
HENDRIK geht allein durch die leere Straße. Er wirkt verloren trotz seines Pelzmantels.
Herbstblätter wehen über das Pflaster.

        HENDRIK
  (zu sich selbst)
  Was bin ich geworden?

INT. GARDEROBE - NACHT

Spiegel überall. Schminktische mit Glühbirnen.
HENDRIK sitzt allein vor dem großen Spiegel und betrachtet sein Mephisto-Kostüm.
Das Licht flackert leicht.

        HENDRIK
  (zum Spiegel)
  Wer bist du? Wer bin ich?
  Bin ich Mephisto – oder ist Mephisto ich?
"""
        drehbuch_pfad = "/tmp/demo_drehbuch.txt"
        with open(drehbuch_pfad, "w", encoding="utf-8") as f:
            f.write(demo_text)
        titel = "MEPHISTO"
    else:
        drehbuch_pfad = args.drehbuch
        titel = Path(drehbuch_pfad).stem.upper().replace("_", " ")

    # Drehbuch laden
    print(f"📖  Lese Drehbuch: {drehbuch_pfad}")
    with open(drehbuch_pfad, "r", encoding="utf-8") as f:
        text = f.read()

    # Szenen parsen
    szenen = parse_drehbuch(text)
    if not szenen:
        print("⚠️  Keine Szenen gefunden! Prüfe das Format (INT./EXT. Szenenkopf).")
        sys.exit(1)
    print(f"🎬  {len(szenen)} Szene(n) gefunden.")

    # Frames erzeugen
    frames = []
    print("🖼️   Erzeuge Storyboard-Karten...")
    frames.append(zeichne_titel(titel, len(szenen)))

    for i, szene in enumerate(szenen, 1):
        print(f"    Szene {i}/{len(szenen)}: {szene['kopf'][:60]}")
        frames.append(zeichne_karte(szene, len(szenen)))

    frames.append(zeichne_abschluss())

    # MP4 exportieren
    print(f"\n🎞️   Exportiere MP4 ({len(frames)} Frames, {args.dauer}s pro Frame)...")
    exportiere_mp4(frames, args.ausgabe, fps=24, dauer_pro_frame=args.dauer)

    print(f"\n✨  Fertig!")
    print(f"    Datei: {args.ausgabe}")
    print(f"    Szenen: {len(szenen)}")
    print(f"    Dauer: ~{(len(frames) * args.dauer):.0f} Sekunden")
    print(f"\n💡  Tipp: Kopiere die Image-Prompts aus dem Video und")
    print(f"    generiere Bilder mit Midjourney, Stable Diffusion oder DALL-E!")


if __name__ == "__main__":
    main()
