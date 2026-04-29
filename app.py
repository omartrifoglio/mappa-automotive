import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium

st.set_page_config(page_title="Mappa Automotive", layout="wide")
st.title("🗺️ Mappa Punti di Interesse Automotive")
st.markdown("Clicca sulla mappa per spostare il centro e calcolare le isocrone stradali.")

ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijg4OGFiOTQ0Y2UyNzQ2YTc4ZWNjODUyZTI0NWJhYjYxIiwiaCI6Im11cm11cjY0In0="

def get_isocrone(lat, lon, distanze_km):
    """Calcola isocrone per distanza stradale tramite ORS"""
    url = "https://api.openrouteservice.org/v2/isochrones/driving-car"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "locations": [[lon, lat]],  # ORS vuole lon, lat (invertito!)
        "range": [d * 1000 for d in distanze_km],  # in metri
        "range_type": "distance",  # distanza stradale, non tempo
        "attributes": ["area"]
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Errore ORS: {response.status_code} — {response.text}")
            return None
    except Exception as e:
        st.error(f"Errore connessione ORS: {e}")
        return None

# Upload file
uploaded = st.file_uploader("Carica il tuo file Excel o CSV", type=["xlsx", "csv"])

if uploaded:
    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)

    st.success(f"✅ Caricati {len(df)} punti")

    # Sidebar
    st.sidebar.header("⚙️ Impostazioni")
    raggi = st.sidebar.multiselect(
        "Distanze stradali (km)",
        options=[2, 5, 10],
        default=[2, 5, 10]
    )
    colore_marker = st.sidebar.color_picker("Colore marker", "#00aa00")

    # Centro iniziale
    if "centro" not in st.session_state:
        st.session_state.centro = [df["Latitudine"].mean(), df["Longitudine"].mean()]

    centro = st.session_state.centro

    # Crea mappa
    mappa = folium.Map(
        location=centro,
        zoom_start=12,
        tiles="CartoDB positron"
    )

    # Calcola e disegna isocrone
    if raggi:
        with st.spinner("⏳ Calcolo isocrone stradali in corso..."):
            isocrone = get_isocrone(centro[0], centro[1], sorted(raggi, reverse=True))

        if isocrone and "features" in isocrone:
            colori = {
                0: {"color": "red",    "fill": "#ff000033", "label": f"{sorted(raggi, reverse=True)[0]} km"},
                1: {"color": "orange", "fill": "#ffa50033", "label": f"{sorted(raggi, reverse=True)[1]} km" if len(raggi) > 1 else ""},
                2: {"color": "blue",   "fill": "#0000ff22", "label": f"{sorted(raggi, reverse=True)[2]} km" if len(raggi) > 2 else ""},
            }
            for i, feature in enumerate(isocrone["features"]):
                if i in colori:
                    folium.GeoJson(
                        feature,
                        style_function=lambda x, c=colori[i]: {
                            "color": c["color"],
                            "fillColor": c["fill"],
                            "weight": 2,
                            "fillOpacity": 0.15
                        },
                        tooltip=f"Raggio stradale {colori[i]['label']}"
                    ).add_to(mappa)
        else:
            st.warning("⚠️ Isocrone non disponibili — controlla la API key ORS")

    # Marker punti di interesse
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row["Latitudine"], row["Longitudine"]],
            radius=6,
            color=colore_marker,
            fill=True,
            fill_opacity=0.8,
            popup=folium.Popup(f"""
                <b>{row.get('Nome', 'N/D')}</b><br>
                {row.get('Indirizzo', 'N/D')}<br>
                ⭐ {row.get('Rating', 'N/D')}
            """, max_width=200),
            tooltip=row.get("Nome", "")
        ).add_to(mappa)

    # Marker centro
    folium.Marker(
        location=centro,
        icon=folium.Icon(color="red", icon="home", prefix="fa"),
        popup="📍 Centro selezionato"
    ).add_to(mappa)

    # Legenda
    legenda = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
         background: white; padding: 12px 16px; border-radius: 8px;
         box-shadow: 0 2px 8px rgba(0,0,0,0.3); font-size: 13px;">
        <b>🗺️ Isocrone stradali</b><br><br>
        <span style="color:blue">●</span> 2 km stradali<br>
        <span style="color:orange">●</span> 5 km stradali<br>
        <span style="color:red">●</span> 10 km stradali<br>
        <span style="color:green">●</span> Punto di interesse<br><br>
        <i style="color:#666; font-size:11px">👆 Clicca per spostare il centro</i>
    </div>
    """
    mappa.get_root().html.add_child(folium.Element(legenda))

    # Mostra mappa
    output = st_folium(mappa, width="100%", height=600)

    # Aggiorna centro al click
    if output and output.get("last_clicked"):
        st.session_state.centro = [
            output["last_clicked"]["lat"],
            output["last_clicked"]["lng"]
        ]
        st.rerun()

    # Tabella punti filtrati per distanza in linea d'aria
    # (approssimazione — le isocrone stradali sono sul rendering)
    if raggi:
        st.subheader("📋 Punti nel raggio selezionato")
        from math import radians, sin, cos, sqrt, atan2

        def distanza_m(lat1, lon1, lat2, lon2):
            R = 6371000
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            a = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
            return R * 2 * atan2(sqrt(a), sqrt(1-a))

        cx, cy = st.session_state.centro
        df["Distanza (m)"] = df.apply(
            lambda r: distanza_m(cx, cy, r["Latitudine"], r["Longitudine"]), axis=1
        ).round(0).astype(int)

        raggio_sel = st.selectbox("Filtra tabella per raggio:", sorted(raggi), format_func=lambda x: f"{x} km")
        df_filtrato = df[df["Distanza (m)"] <= raggio_sel * 1000].sort_values("Distanza (m)")
        st.dataframe(df_filtrato[["Nome", "Indirizzo", "Rating", "Distanza (m)"]].reset_index(drop=True))
        st.caption(f"Trovati {len(df_filtrato)} punti entro ~{raggio_sel} km")

else:
    st.info("👆 Carica un file Excel o CSV per iniziare")

