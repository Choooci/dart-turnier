import streamlit as st
import pandas as pd
from supabase import create_client

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
            passwort = st.text_input(
                "Passwort",
                type="password",
                placeholder="Passwort eingeben..."
            )
            submit = st.form_submit_button("🔓 Einloggen", use_container_width=True)

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

    spieler = ["Claas", "Pätte", "Jakob", "Felix", "Jonas", "Chrissi", "Flo", "Dwain"]
    stats = {s: {"Punkte": 0, "Siege": 0, "Niederlagen": 0, "Unentschieden": 0,
                 "Legs+": 0, "Legs-": 0, "Spiele": 0, "Avg_sum": 0.0, "Avg_n": 0} 
             for s in spieler}

    for e in ergebnisse:
        h, g = e["heim"], e["gast"]
        lh, lg = e["legs_heim"], e["legs_gast"]
        if h not in stats or g not in stats:
            continue

        stats[h]["Spiele"] += 1
        stats[g]["Spiele"] += 1
        stats[h]["Legs+"] += lh
        stats[h]["Legs-"] += lg
        stats[g]["Legs+"] += lg
        stats[g]["Legs-"] += lh

        # Average
        if e["avg_heim"] > 0:
            stats[h]["Avg_sum"] += e["avg_heim"]
            stats[h]["Avg_n"]   += 1
        if e["avg_gast"] > 0:
            stats[g]["Avg_sum"] += e["avg_gast"]
            stats[g]["Avg_n"]   += 1

        # Punkte
        if lh > lg:
            stats[h]["Punkte"] += 2
            stats[h]["Siege"]  += 1
            stats[g]["Niederlagen"] += 1
        elif lg > lh:
            stats[g]["Punkte"] += 2
            stats[g]["Siege"]  += 1
            stats[h]["Niederlagen"] += 1
        else:
            stats[h]["Punkte"] += 1
            stats[g]["Punkte"] += 1
            stats[h]["Unentschieden"] += 1
            stats[g]["Unentschieden"] += 1

    rows = []
    for s, v in stats.items():
        avg = round(v["Avg_sum"] / v["Avg_n"], 2) if v["Avg_n"] > 0 else 0
        rows.append({
            "Spieler":        s,
            "Spiele":         v["Spiele"],
            "S":              v["Siege"],
            "U":              v["Unentschieden"],
            "N":              v["Niederlagen"],
            "Legs +/-":       f"{v['Legs+']}:{v['Legs-']}",
            "Punkte":         v["Punkte"],
            "Ø Average":      avg
        })

    df = pd.DataFrame(rows).sort_values(
        ["Punkte", "S", "Ø Average"], ascending=False
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
        df.style.apply(style_tabelle, axis=1),
        use_container_width=True
    )

# ─────────────────────────────────────────────
# Spielplan anzeigen
# ─────────────────────────────────────────────
def zeige_spielplan(spielplan, ergebnisse):
    st.header("📅 Spielplan")

    # Ergebnisse als schnelle Lookup-Map
    erg_map = {}
    for e in ergebnisse:
        key = (e["spieltag"], e["heim"], e["gast"])
        erg_map[key] = e

    spieltage = sorted(set(s["spieltag"] for s in spielplan))

    for st_nr in spieltage:
        spiele = [s for s in spielplan if s["spieltag"] == st_nr]
        start  = spiele[0]["start_datum"]
        ende   = spiele[0]["end_datum"]

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
                    st.caption(
                        f"Avg: {e['avg_heim']} | {e['avg_gast']} – "
                        f"Checkout: {e['checkout_heim']}% | {e['checkout_gast']}% – "
                        f"26er: {e['er_26_heim']} | {e['er_26_gast']}"
                    )
                st.markdown("---")

# ─────────────────────────────────────────────
# Ergebnis eintragen
# ─────────────────────────────────────────────
def trage_ergebnis_ein(spielplan, ergebnisse):
    st.header("✏️ Ergebnis eintragen")

    # Bereits eingetragene Spiele
    erg_keys = {(e["spieltag"], e["heim"], e["gast"]) for e in ergebnisse}

    spieltage = sorted(set(s["spieltag"] for s in spielplan))
    spieltag  = st.selectbox("Spieltag wählen", spieltage, format_func=lambda x: f"Spieltag {x}")

    spiele_heute = [s for s in spielplan if s["spieltag"] == spieltag]
    optionen     = [f"{s['heim']} vs {s['gast']}" for s in spiele_heute]
    auswahl      = st.selectbox("Spiel wählen", optionen)

    idx   = optionen.index(auswahl)
    spiel = spiele_heute[idx]
    key   = (spiel["spieltag"], spiel["heim"], spiel["gast"])

    # Vorhandene Daten laden
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
                                            value=vorhandene["avg_heim"] if vorhandene else 0.0, key="ah")
            checkout_heim = st.number_input("Checkout %", min_value=0.0, max_value=100.0, step=0.01,
                                            value=vorhandene["checkout_heim"] if vorhandene else 0.0, key="ch")
            er_26_heim    = st.number_input("26er", min_value=0,
                                            value=vorhandene["er_26_heim"] if vorhandene else 0, key="z6h")
            hc_heim       = st.checkbox("High-Check (>100)", 
                                        value=vorhandene["highcheck_heim"] if vorhandene else False, key="hch")

        with col2:
            st.markdown(f"**{spiel['gast']}**")
            legs_gast     = st.number_input("Legs", min_value=0, max_value=10,
                                            value=vorhandene["legs_gast"] if vorhandene else 0, key="lg")
            avg_gast      = st.number_input("Average", min_value=0.0, max_value=200.0, step=0.01,
                                            value=vorhandene["avg_gast"] if vorhandene else 0.0, key="ag")
            checkout_gast = st.number_input("Checkout %", min_value=0.0, max_value=100.0, step=0.01,
                                            value=vorhandene["checkout_gast"] if vorhandene else 0.0, key="cg")
            er_26_gast    = st.number_input("26er", min_value=0,
                                            value=vorhandene["er_26_gast"] if vorhandene else 0, key="z6g")
            hc_gast       = st.checkbox("High-Check (>100)",
                                        value=vorhandene["highcheck_gast"] if vorhandene else False, key="hcg")

        submit = st.form_submit_button("💾 Speichern", use_container_width=True)

    if submit:
        daten = {
            "spieltag":      spiel["spieltag"],
            "heim":          spiel["heim"],
            "gast":          spiel["gast"],
            "legs_heim":     legs_heim,
            "legs_gast":     legs_gast,
            "avg_heim":      avg_heim,
            "avg_gast":      avg_gast,
            "checkout_heim": checkout_heim,
            "checkout_gast": checkout_gast,
            "er_26_heim":    er_26_heim,
            "er_26_gast":    er_26_gast,
            "highcheck_heim": hc_heim,
            "highcheck_gast": hc_gast
        }

        if vorhandene:
            supabase.table("ergebnisse").update(daten).eq("id", vorhandene["id"]).execute()
            st.success("✅ Ergebnis aktualisiert!")
        else:
            supabase.table("ergebnisse").insert(daten).execute()
            st.success("✅ Ergebnis gespeichert!")

        st.rerun()

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

    for e in ergebnisse:
        if e["heim"] == spieler:
            ist_heim = True
        elif e["gast"] == spieler:
            ist_heim = False
        else:
            continue

        l_p   = e["legs_heim"] if ist_heim else e["legs_gast"]
        l_m   = e["legs_gast"] if ist_heim else e["legs_heim"]
        avg   = e["avg_heim"]  if ist_heim else e["avg_gast"]
        co    = e["checkout_heim"] if ist_heim else e["checkout_gast"]
        z26   = e["er_26_heim"]    if ist_heim else e["er_26_gast"]
        hc    = e["highcheck_heim"] if ist_heim else e["highcheck_gast"]
        gegner = e["gast"] if ist_heim else e["heim"]

        legs_p    += l_p
        legs_m    += l_m
        gesamt_26 += z26

        if avg > 0:      avgs.append(avg)
        if co > 0:       checkouts.append(co)

        if l_p > l_m:
            status = "✅ Sieg"
            punkte += 2
        elif l_p < l_m:
            status = "❌ Niederlage"
        else:
            status = "🤝 Unentschieden"
            punkte += 1

        rows.append({
            "Spieltag": e["spieltag"],
            "Gegner":   gegner,
            "Legs":     f"{l_p}:{l_m}",
            "Punkte":   punkte,
            "Status":   status,
            "Average":  avg,
            "Checkout %": co,
            "26er":     z26,
            "High-Check": "✅" if hc else ""
        })

    # KPI-Kacheln
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("🏆 Punkte",        punkte)
    c2.metric("✅ Siege",          sum(1 for r in rows if r["Status"] == "✅ Sieg"))
    c3.metric("📊 Legs +/-",      f"{legs_p}/{legs_m}")
    c4.metric("🎯 Ø Average",     round(sum(avgs)/len(avgs), 2)           if avgs       else 0)
    c5.metric("💯 Ø Checkout %",  round(sum(checkouts)/len(checkouts), 2) if checkouts  else 0)
    c6.metric("🔢 26er gesamt",   gesamt_26)

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
# Haupt-App
# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Dart Turnier 2026",
        page_icon="🎯",
        layout="wide"
    )

    if not check_passwort():
        st.stop()

    # Header mit Logout
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

    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 Tabelle",
        "📅 Spielplan",
        "✏️ Ergebnis eintragen",
        "📊 Statistiken"
    ])

    with tab1:
        zeige_tabelle(ergebnisse)

    with tab2:
        zeige_spielplan(spielplan, ergebnisse)

    with tab3:
        trage_ergebnis_ein(spielplan, ergebnisse)

    with tab4:
        zeige_statistiken(ergebnisse)

if __name__ == "__main__":
    main()
