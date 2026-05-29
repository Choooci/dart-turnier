import streamlit as st
import pandas as pd
from supabase import create_client

# ─────────────────────────────────────────────
# Light Mode erzwingen
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dart Turnier 2026",
    page_icon="🎯",
    layout="wide"
)

# ─────────────────────────────────────────────
# Verbindung zu Supabase
# ─────────────────────────────────────────────
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# ─────────────────────────────────────────────
# Passwort-Schutz
# ─────────────────────────────────────────────
def check_passwort():
    if st.session_state.get("eingeloggt"):
        return True

    st.title("🎯 Dart Turnier 2026")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔒 Login")
        with st.form("login_form"):
            passwort = st.text_input("Passwort", type="password", placeholder="Passwort eingeben...")
            submit   = st.form_submit_button("🔓 Einloggen", use_container_width=True)

        if submit:
            if passwort == st.secrets["APP_PASSWORT"]:
                st.session_state["eingeloggt"] = True
                st.rerun()
            else:
                st.error("❌ Falsches Passwort!")

    return False

# ─────────────────────────────────────────────
# Daten laden
# ─────────────────────────────────────────────
def lade_spielplan():
    res = supabase.table("spielplan").select("*").order("spieltag").execute()
    return res.data

def lade_ergebnisse():
    res = supabase.table("ergebnisse").select("*").execute()
    return res.data

# ─────────────────────────────────────────────
# Tabelle berechnen
# ─────────────────────────────────────────────
def zeige_tabelle(ergebnisse):
    st.header("🏆 Tabelle")

    spieler_liste = ["Claas", "Pätte", "Jakob", "Felix", "Jonas", "Chrissi", "Flo", "Dwain"]
    stats = {s: {"Punkte": 0, "Siege": 0, "Niederlagen": 0, "Unentschieden": 0,
                 "Legs+": 0, "Legs-": 0, "Spiele": 0,
                 "Avg_sum": 0.0, "Avg_n": 0,
                 "26er": 0, "Highchecks": [], "Best_HC": 0}
             for s in spieler_liste}

    for e in ergebnisse:
        h, g = e["heim"], e["gast"]
        lh, lg = e["legs_heim"], e["legs_gast"]
        if h not in stats or g not in stats:
            continue

        stats[h]["Spiele"] += 1
        stats[g]["Spiele"] += 1
        stats[h]["Legs+"]  += lh
        stats[h]["Legs-"]  += lg
        stats[g]["Legs+"]  += lg
        stats[g]["Legs-"]  += lh
        stats[h]["26er"]   += e.get("er_26_heim", 0)
        stats[g]["26er"]   += e.get("er_26_gast", 0)

        # High-Checks (Liste von Zahlen)
        for hc in (e.get("highcheck_heim") or []):
            if isinstance(hc, (int, float)) and hc > 0:
                stats[h]["Highchecks"].append(hc)
        for hc in (e.get("highcheck_gast") or []):
            if isinstance(hc, (int, float)) and hc > 0:
                stats[g]["Highchecks"].append(hc)

        if e["avg_heim"] > 0:
            stats[h]["Avg_sum"] += e["avg_heim"]
            stats[h]["Avg_n"]   += 1
        if e["avg_gast"] > 0:
            stats[g]["Avg_sum"] += e["avg_gast"]
            stats[g]["Avg_n"]   += 1

        if lh > lg:
            stats[h]["Punkte"] += 2; stats[h]["Siege"] += 1
            stats[g]["Niederlagen"] += 1
        elif lg > lh:
            stats[g]["Punkte"] += 2; stats[g]["Siege"] += 1
            stats[h]["Niederlagen"] += 1
        else:
            stats[h]["Punkte"] += 1; stats[g]["Punkte"] += 1
            stats[h]["Unentschieden"] += 1; stats[g]["Unentschieden"] += 1

    rows = []
    for s, v in stats.items():
        avg     = round(v["Avg_sum"] / v["Avg_n"], 2) if v["Avg_n"] > 0 else 0.0
        best_hc = max(v["Highchecks"]) if v["Highchecks"] else "-"
        rows.append({
            "Spieler":       s,
            "Spiele":        v["Spiele"],
            "S":             v["Siege"],
            "U":             v["Unentschieden"],
            "N":             v["Niederlagen"],
            "Legs +/-":      f"{v['Legs+']}:{v['Legs-']}",
            "Punkte":        v["Punkte"],
            "Ø Avg":         avg,
            "26er":          v["26er"],
            "Best HC":       best_hc,
        })

    df = pd.DataFrame(rows).sort_values(
        ["Punkte", "S", "Ø Avg"], ascending=False
    ).reset_index(drop=True)
    df.index += 1

    def style_tabelle(row):
        if row.name == 1:
            return ["background-color: #FFD700; color: black"] * len(row)
        elif row.name == 2:
            return ["background-color: #C0C0C0; color: black"] * len(row)
        elif row.name == 3:
            return ["background-color: #CD7F32; color: black"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df.style.apply(style_tabelle, axis=1).format({"Ø Avg": "{:.2f}"}),
        use_container_width=True
    )

    # ── Preise & Awards ──────────────────────────────────
    st.markdown("---")
    st.subheader("🏅 Preise & Awards")

    # Werte berechnen
    sorted_rows = sorted(rows, key=lambda x: (x["Punkte"], x["S"], x["Ø Avg"]), reverse=True)

    platz1 = sorted_rows[0]["Spieler"] if len(sorted_rows) > 0 else "–"
    platz2 = sorted_rows[1]["Spieler"] if len(sorted_rows) > 1 else "–"
    platz3 = sorted_rows[2]["Spieler"] if len(sorted_rows) > 2 else "–"

    krone_26  = max(rows, key=lambda x: x["26er"])
    best_avg  = max(rows, key=lambda x: x["Ø Avg"])

    # Bestes High-Check über alle
    best_hc_val  = 0
    best_hc_name = "–"
    for e in ergebnisse:
        for hc in (e.get("highcheck_heim") or []):
            if isinstance(hc, (int, float)) and hc > best_hc_val:
                best_hc_val  = hc
                best_hc_name = e["heim"]
        for hc in (e.get("highcheck_gast") or []):
            if isinstance(hc, (int, float)) and hc > best_hc_val:
                best_hc_val  = hc
                best_hc_name = e["gast"]

    hc_label = f"{best_hc_name} ({best_hc_val})" if best_hc_val > 0 else "Noch offen"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"🏆 **Platz 1 – 15 €**\n\n{platz1}")
        st.markdown(f"🥈 **Platz 2 – 8 €**\n\n{platz2}")
        st.markdown(f"🥉 **Platz 3 – 4 €**\n\n{platz3}")
    with col2:
        st.markdown(f"👑 **26er-Krone – 5 €**\n\n{krone_26['Spieler']} ({krone_26['26er']} Stück)")
        st.markdown(f"📊 **Best Average – 4 €**\n\n{best_avg['Spieler']} ({best_avg['Ø Avg']:.2f})")
    with col3:
        st.markdown(f"🚀 **High-Finish-Award – 4 €**\n\n{hc_label}")

# ─────────────────────────────────────────────
# Spielplan anzeigen
# ─────────────────────────────────────────────
from datetime import datetime

def format_datum(datum_str):
    # Datum von ISO-Format in lesbares deutsches Format umwandeln
    dt = datetime.strptime(datum_str, "%Y-%m-%d")
    return dt.strftime("%-d. %B %Y").replace("January","Januar").replace("February","Februar")\
        .replace("March","März").replace("April","April").replace("May","Mai")\
        .replace("June","Juni").replace("July","Juli").replace("August","August")\
        .replace("September","September").replace("October","Oktober")\
        .replace("November","November").replace("December","Dezember")

def zeige_spielplan(spielplan, ergebnisse):
    st.header("📅 Spielplan")

    erg_map = {}
    for e in ergebnisse:
        key = (e["spieltag"], e["heim"], e["gast"])
        erg_map[key] = e

    spieltage = sorted(set(s["spieltag"] for s in spielplan))

    for st_nr in spieltage:
        spiele = [s for s in spielplan if s["spieltag"] == st_nr]
        start  = format_datum(spiele[0]["start_datum"])
        ende   = format_datum(spiele[0]["end_datum"])

        with st.expander(f"📅 Spieltag {st_nr} | {start} – {ende}", expanded=(st_nr == 1)):
            for spiel in spiele:
                key = (spiel["spieltag"], spiel["heim"], spiel["gast"])
                e   = erg_map.get(key)

                col1, col2, col3 = st.columns([3, 2, 3])
                with col1:
                    st.markdown(f"**{spiel['heim']}**")
                with col2:
                    if e:
                        st.markdown(
                            f"<div style='text-align:center; font-size:1.2em; font-weight:bold'>"
                            f"{e['legs_heim']} : {e['legs_gast']}</div>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            "<div style='text-align:center; color:gray'>vs</div>",
                            unsafe_allow_html=True
                        )
                with col3:
                    st.markdown(f"**{spiel['gast']}**")

                if e:
                    hc_h = e.get("highcheck_heim") or []
                    hc_g = e.get("highcheck_gast") or []
                    hc_str = ""
                    if hc_h or hc_g:
                        hc_str = f" – HC: {hc_h} | {hc_g}"
                    st.caption(
                        f"Avg: {e['avg_heim']:.2f} | {e['avg_gast']:.2f} – "
                        f"Checkout: {e['checkout_heim']}% | {e['checkout_gast']}% – "
                        f"26er: {e['er_26_heim']} | {e['er_26_gast']}"
                        f"{hc_str}"
                    )
                st.markdown("---")



# ─────────────────────────────────────────────
# Ergebnis eintragen
# ─────────────────────────────────────────────
def trage_ergebnis_ein(spielplan, ergebnisse):
    st.header("✏️ Ergebnis eintragen")

    if not spielplan:
        st.warning("Kein Spielplan gefunden.")
        return

    spieltage = sorted(set(s["spieltag"] for s in spielplan))
    spieltag  = st.selectbox(
        "Spieltag wählen", spieltage,
        format_func=lambda x: f"Spieltag {x}",
        key="spieltag_auswahl"
    )

    spiele_heute = [s for s in spielplan if s["spieltag"] == spieltag]
    optionen     = [f"{s['heim']} vs {s['gast']}" for s in spiele_heute]

    if not optionen:
        st.warning("Keine Spiele für diesen Spieltag gefunden.")
        return

    auswahl = st.selectbox("Spiel wählen", optionen, key=f"spiel_auswahl_{spieltag}")

    try:
        idx = optionen.index(auswahl)
    except ValueError:
        st.warning("Bitte Spieltag neu auswählen.")
        st.rerun()
        return

    spiel = spiele_heute[idx]
    key   = (spiel["spieltag"], spiel["heim"], spiel["gast"])

    vorhandene = None
    for e in ergebnisse:
        if (e["spieltag"], e["heim"], e["gast"]) == key:
            vorhandene = e
            break

    if vorhandene:
        st.info("ℹ️ Dieses Spiel wurde bereits eingetragen. Du kannst es überschreiben.")

    st.markdown(f"### {spiel['heim']} vs {spiel['gast']}")

    with st.form("ergebnis_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**{spiel['heim']}**")
            legs_heim     = st.number_input("Legs", min_value=0, max_value=10,
                                            value=vorhandene["legs_heim"] if vorhandene else 0, key="lh")
            avg_heim      = st.number_input("Average", min_value=0.0, max_value=200.0, step=0.01,
                                            value=float(vorhandene["avg_heim"]) if vorhandene else 0.0, key="ah")
            checkout_heim = st.number_input("Checkout %", min_value=0.0, max_value=100.0, step=0.01,
                                            value=float(vorhandene["checkout_heim"]) if vorhandene else 0.0, key="ch")
            er_26_heim    = st.number_input("26er", min_value=0,
                                            value=vorhandene["er_26_heim"] if vorhandene else 0, key="z6h")
            # High-Checks als kommagetrennte Zahlen eingeben
            hc_heim_default = ", ".join(str(x) for x in (vorhandene.get("highcheck_heim") or [])) if vorhandene else ""
            hc_heim_str     = st.text_input(
                "High-Checks (>100), kommagetrennt z.B. 102, 115",
                value=hc_heim_default, key="hch"
            )

        with col2:
            st.markdown(f"**{spiel['gast']}**")
            legs_gast     = st.number_input("Legs", min_value=0, max_value=10,
                                            value=vorhandene["legs_gast"] if vorhandene else 0, key="lg")
            avg_gast      = st.number_input("Average", min_value=0.0, max_value=200.0, step=0.01,
                                            value=float(vorhandene["avg_gast"]) if vorhandene else 0.0, key="ag")
            checkout_gast = st.number_input("Checkout %", min_value=0.0, max_value=100.0, step=0.01,
                                            value=float(vorhandene["checkout_gast"]) if vorhandene else 0.0, key="cg")
            er_26_gast    = st.number_input("26er", min_value=0,
                                            value=vorhandene["er_26_gast"] if vorhandene else 0, key="z6g")
            hc_gast_default = ", ".join(str(x) for x in (vorhandene.get("highcheck_gast") or [])) if vorhandene else ""
            hc_gast_str     = st.text_input(
                "High-Checks (>100), kommagetrennt z.B. 102, 115",
                value=hc_gast_default, key="hcg"
            )

        submit = st.form_submit_button("💾 Speichern", use_container_width=True)

    if submit:
        # High-Checks parsen
        def parse_hc(s):
            result = []
            for x in s.split(","):
                x = x.strip()
                if x.isdigit():
                    result.append(int(x))
            return result

        daten = {
            "spieltag":       spiel["spieltag"],
            "heim":           spiel["heim"],
            "gast":           spiel["gast"],
            "legs_heim":      int(legs_heim),
            "legs_gast":      int(legs_gast),
            "avg_heim":       float(avg_heim),
            "avg_gast":       float(avg_gast),
            "checkout_heim":  float(checkout_heim),
            "checkout_gast":  float(checkout_gast),
            "er_26_heim":     int(er_26_heim),
            "er_26_gast":     int(er_26_gast),
            "highcheck_heim": parse_hc(hc_heim_str),
            "highcheck_gast": parse_hc(hc_gast_str),
        }

        try:
            if vorhandene:
                supabase.table("ergebnisse").update(daten).eq("id", vorhandene["id"]).execute()
                st.success("✅ Ergebnis aktualisiert!")
            else:
                supabase.table("ergebnisse").insert(daten).execute()
                st.success("✅ Ergebnis gespeichert!")
            st.rerun()
        except Exception as ex:
            st.error(f"❌ Fehler beim Speichern: {ex}")

# ─────────────────────────────────────────────
# Statistiken
# ─────────────────────────────────────────────
def zeige_statistiken(ergebnisse):
    st.header("📊 Statistiken")

    spieler_liste = ["Claas", "Pätte", "Jakob", "Felix", "Jonas", "Chrissi", "Flo", "Dwain"]
    spieler       = st.selectbox("Spieler wählen", spieler_liste)

    rows      = []
    avgs      = []
    checkouts = []
    punkte    = 0
    legs_p    = 0
    legs_m    = 0
    gesamt_26 = 0
    alle_hc   = []

    for e in ergebnisse:
        if e["heim"] == spieler:
            ist_heim = True
        elif e["gast"] == spieler:
            ist_heim = False
        else:
            continue

        l_p  = e["legs_heim"] if ist_heim else e["legs_gast"]
        l_m  = e["legs_gast"] if ist_heim else e["legs_heim"]
        avg  = e["avg_heim"]  if ist_heim else e["avg_gast"]
        co   = e["checkout_heim"] if ist_heim else e["checkout_gast"]
        z26  = e["er_26_heim"]    if ist_heim else e["er_26_gast"]
        hc_liste = (e.get("highcheck_heim") or []) if ist_heim else (e.get("highcheck_gast") or [])
        gegner   = e["gast"] if ist_heim else e["heim"]

        legs_p    += l_p
        legs_m    += l_m
        gesamt_26 += z26
        alle_hc   += [x for x in hc_liste if isinstance(x, (int, float)) and x > 0]

        if avg > 0: avgs.append(avg)
        if co > 0:  checkouts.append(co)

        if l_p > l_m:
            status = "✅ Sieg"; punkte += 2
        elif l_p < l_m:
            status = "❌ Niederlage"
        else:
            status = "🤝 Unentschieden"; punkte += 1

        rows.append({
            "Spieltag":   e["spieltag"],
            "Gegner":     gegner,
            "Legs":       f"{l_p}:{l_m}",
            "Status":     status,
            "Average":    round(avg, 2),
            "Checkout %": co,
            "26er":       z26,
            "High-Checks": ", ".join(str(x) for x in hc_liste) if hc_liste else ""
        })

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("🏆 Punkte",       punkte)
    c2.metric("✅ Siege",         sum(1 for r in rows if r["Status"] == "✅ Sieg"))
    c3.metric("📊 Legs +/-",     f"{legs_p}/{legs_m}")
    c4.metric("🎯 Ø Average",    round(sum(avgs)/len(avgs), 2)           if avgs      else 0)
    c5.metric("💯 Ø Checkout %", round(sum(checkouts)/len(checkouts), 2) if checkouts else 0)
    c6.metric("🔢 26er",         gesamt_26)
    c7.metric("🚀 Best HC",      max(alle_hc) if alle_hc else "–")

    if rows:
        st.subheader("Spielübersicht")
        df = pd.DataFrame(rows).sort_values("Spieltag")
        st.dataframe(df, use_container_width=True, hide_index=True)

        if len(avgs) > 1:
            st.subheader("📈 Average-Verlauf")
            avg_df = pd.DataFrame({
                "Spieltag": [r["Spieltag"] for r in rows if r["Average"] > 0],
                "Average":  [r["Average"]  for r in rows if r["Average"] > 0]
            })
            st.line_chart(avg_df.set_index("Spieltag"))
    else:
        st.info("Noch keine Spiele eingetragen.")

# ─────────────────────────────────────────────
# Info-Tab
# ─────────────────────────────────────────────
def zeige_info():
    st.header("ℹ️ Infos & Regeln")

    st.markdown("""
    ### 🎯 Modus
    - **Jeder gegen Jeden** – 8 Spieler, gespielt wird in Spieltagen (je 2 Wochen)
    - **Format:** Best of 8 · 501 · Double Out
    - **Punkte:** Sieg = 2 Pkt · Unentschieden = 1 Pkt · Niederlage = 0 Pkt

    ### 💻 Plattform
    - Gespielt wird auf **[lidarts.org](https://lidarts.org)** – bitte rechtzeitig registrieren!
    - Begleitend empfehlen wir einen **WhatsApp Videocall** während des Spiels

    ### 💰 Preisgeld (Gesamt: 40 €)
    | Award | Preis |
    |---|---|
    | 🏆 Platz 1 – Gesamttabelle | 15 € |
    | 🥈 Platz 2 | 8 € |
    | 🥉 Platz 3 | 4 € |
    | 👑 26er-Krone (meiste 26er) | 5 € |
    | 🚀 High-Finish-Award (höchstes Finish >100) | 4 € |
    | 📊 Best-Average-Award | 4 € |

    ### 💳 TN-Gebühr
    Einmalig **5 €** per PayPal an: `dwainschwarzer575@gmail.com`

    ---
    🔥 **GAME ON – Pfeile spitz, Bier kalt!** 🎯
    """)

# ─────────────────────────────────────────────
# Haupt-App
# ─────────────────────────────────────────────
def main():
    if not check_passwort():
        st.stop()

    col1, col2 = st.columns([9, 1])
    with col1:
        st.title("🎯 Dart Turnier 2026")
    with col2:
        if st.button("🚪 Logout"):
            st.session_state["eingeloggt"] = False
            st.rerun()

    st.markdown("---")

    spielplan  = lade_spielplan()
    ergebnisse = lade_ergebnisse()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏆 Tabelle",
        "📅 Spielplan",
        "✏️ Ergebnis eintragen",
        "📊 Statistiken",
        "ℹ️ Infos & Regeln"
    ])

    with tab1:
        zeige_tabelle(ergebnisse)
    with tab2:
        zeige_spielplan(spielplan, ergebnisse)
    with tab3:
        trage_ergebnis_ein(spielplan, ergebnisse)
    with tab4:
        zeige_statistiken(ergebnisse)
    with tab5:
        zeige_info()

if __name__ == "__main__":
    main()
