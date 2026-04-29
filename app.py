import streamlit as st
import folium
import pandas as pd
from streamlit_folium import st_folium

st.set_page_config(page_title="Mappa Automotive", layout="wide")
st.title("🗺️ Mappa Punti di Interesse Automotive")
st.markdown("Clicca sulla mappa per spostare il centro e vedere i punti nel raggio selezionato.")

# Upload file
uploaded = st.file_uploader("Carica il tuo file Excel o CSV", type=["xlsx", "csv"])

if uploaded:
    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)

    st.success(f"✅ Caricati {len(df)} punti")

    # Sidebar controlli
    st.sidebar.header("⚙️ Impostazioni")
    raggi = st.sidebar.multiselect(
        "Raggi da visualizzare (km)",
        options=[2, 5, 10],
        default=[2, 5, 10]
    )

    colore_marker = st.sidebar.color_picker("Colore marker", "#00aa00")

    # Centro iniziale
    centro_lat = df["Latitudine"].mean()
    centro_lon = df["Longitudine"].mean()

    # Crea mappa
    mappa = folium.Map(
        location=[centro_lat, centro_lon],
        zoom_start=11,
        tiles="CartoDB positron"  # alternativa a OpenStreetMap, senza restrizioni
    )

    # Aggiungi marker
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

    # Aggiungi cerchi se c'è stato un click
    colori_raggi = {2: "blue", 5: "orange", 10: "red"}

    if "centro" not in st.session_state:
        st.session_state.centro = [centro_lat, centro_lon]

    for km in raggi:
        folium.Circle(
            location=st.session_state.centro,
            radius=km * 1000,
            color=colori_raggi[km],
            fill=True,
            fill_opacity=0.06,
            weight=2,
            tooltip=f"Raggio {km} km"
        ).add_to(mappa)

    # Marker centro
    folium.Marker(
        location=st.session_state.centro,
        icon=folium.Icon(color="red", icon="home", prefix="fa"),
        popup="📍 Centro selezionato"
    ).add_to(mappa)

    # Mostra mappa e cattura click
    output = st_folium(mappa, width="100%", height=600)

    # Aggiorna centro se l'utente clicca
    if output and output.get("last_clicked"):
        st.session_state.centro = [
            output["last_clicked"]["lat"],
            output["last_clicked"]["lng"]
        ]
        st.rerun()

    # Tabella punti nel raggio selezionato
    st.subheader("📋 Punti nel raggio minimo selezionato")
    if raggi:
        raggio_min = min(raggi) * 1000
        from math import radians, sin, cos, sqrt, atan2

        def distanza_km(lat1, lon1, lat2, lon2):
            R = 6371000
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
            return R * 2 * atan2(sqrt(a), sqrt(1-a))

        cx, cy = st.session_state.centro
        df["Distanza (m)"] = df.apply(
            lambda r: distanza_km(cx, cy, r["Latitudine"], r["Longitudine"]), axis=1
        ).round(0).astype(int)

        raggio_sel = st.selectbox("Filtra per raggio:", raggi, format_func=lambda x: f"{x} km")
        df_filtrato = df[df["Distanza (m)"] <= raggio_sel * 1000].sort_values("Distanza (m)")
        st.dataframe(df_filtrato[["Nome", "Indirizzo", "Rating", "Distanza (m)"]].reset_index(drop=True))
        st.caption(f"Trovati {len(df_filtrato)} punti entro {raggio_sel} km")

else:
    st.info("👆 Carica un file Excel o CSV per iniziare")
