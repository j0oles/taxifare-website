import time
from datetime import datetime

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Taxi Fare Predictor", page_icon="🚕", layout="centered")
st.title("🚕 taxi fare predictor")
st.caption("mets un trajet ➜ la carte se met à jour en live. clique sur **save & predict** pour estimer le prix 💸")

API_URL = "https://wagon-data-tpl-image-129712465951.europe-west1.run.app/predict"
BASEMAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


# -----------------------------
# Helpers
# -----------------------------
def build_params(
    pickup_datetime: datetime,
    pickup_longitude: float,
    pickup_latitude: float,
    dropoff_longitude: float,
    dropoff_latitude: float,
    passenger_count: int,
) -> dict:
    return {
        "pickup_datetime": pickup_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "pickup_longitude": pickup_longitude,
        "pickup_latitude": pickup_latitude,
        "dropoff_longitude": dropoff_longitude,
        "dropoff_latitude": dropoff_latitude,
        "passenger_count": passenger_count,
    }


def call_fare_api(url: str, params: dict) -> float:
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return float(resp.json()["fare"])


@st.cache_data(ttl=60, show_spinner=False)
def get_route_osrm_cached(
    pickup_lon: float,
    pickup_lat: float,
    dropoff_lon: float,
    dropoff_lat: float,
) -> list[list[float]]:
    """
    Route following roads via OSRM.
    Cached to avoid hammering OSRM on every rerun.
    """
    coords = f"{pickup_lon},{pickup_lat};{dropoff_lon},{dropoff_lat}"
    route_url = f"{OSRM_URL}/{coords}"
    params = {"overview": "full", "geometries": "geojson"}

    r = requests.get(route_url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data["routes"][0]["geometry"]["coordinates"]  # [[lon, lat], ...]


def make_map_with_route(
    pickup_lon: float,
    pickup_lat: float,
    dropoff_lon: float,
    dropoff_lat: float,
) -> pdk.Deck:
    points_df = pd.DataFrame(
        [
            {"type": "pickup 📍", "lat": pickup_lat, "lon": pickup_lon},
            {"type": "dropoff 🏁", "lat": dropoff_lat, "lon": dropoff_lon},
        ]
    )

    # route roads (fallback ligne droite si OSRM tombe)
    try:
        route_coords = get_route_osrm_cached(pickup_lon, pickup_lat, dropoff_lon, dropoff_lat)
    except Exception:
        route_coords = [[pickup_lon, pickup_lat], [dropoff_lon, dropoff_lat]]

    route_df = pd.DataFrame([{"path": route_coords}])

    center_lat = (pickup_lat + dropoff_lat) / 2
    center_lon = (pickup_lon + dropoff_lon) / 2

    layers = [
        pdk.Layer(
            "ScatterplotLayer",
            data=points_df,
            get_position="[lon, lat]",
            get_radius=90,
            pickable=True,
        ),
        pdk.Layer(
            "PathLayer",
            data=route_df,
            get_path="path",
            width_scale=20,
            width_min_pixels=3,
            pickable=False,
        ),
    ]

    return pdk.Deck(
        map_style=BASEMAP_STYLE,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=12,
            pitch=0,
        ),
        layers=layers,
        tooltip={"text": "{type}"},
    )


# -----------------------------
# Init default state (so map always has values)
# -----------------------------
defaults = {
    "pickup_datetime": datetime.now(),
    "pickup_longitude": -73.950655,
    "pickup_latitude": 40.783282,
    "dropoff_longitude": -73.984365,
    "dropoff_latitude": 40.769802,
    "passenger_count": 2,
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)


# -----------------------------
# UI (inputs) — NOT a form, so map updates live
# -----------------------------
st.subheader("🧾 ride parameters (live)")

st.datetime_input("🕒 date & time", key="pickup_datetime")

c1, c2 = st.columns(2)
c1.number_input("📍 pickup longitude", key="pickup_longitude", format="%.6f", step=0.000001)
c2.number_input("📍 pickup latitude", key="pickup_latitude", format="%.6f", step=0.000001)

c3, c4 = st.columns(2)
c3.number_input("🏁 dropoff longitude", key="dropoff_longitude", format="%.6f", step=0.000001)
c4.number_input("🏁 dropoff latitude", key="dropoff_latitude", format="%.6f", step=0.000001)

st.number_input("👥 passenger count", key="passenger_count", min_value=1, max_value=8, step=1, format="%d")

# -----------------------------
# Map — ALWAYS visible, updates with inputs
# -----------------------------
st.subheader("🗺️ route preview (roads)")

deck = make_map_with_route(
    st.session_state["pickup_longitude"],
    st.session_state["pickup_latitude"],
    st.session_state["dropoff_longitude"],
    st.session_state["dropoff_latitude"],
)
st.pydeck_chart(deck, use_container_width=True)

# -----------------------------
# Prediction — ONLY when clicking the button
# -----------------------------
st.subheader("💸 fare prediction")

if st.button("🚀 save & predict"):
    params = build_params(
        st.session_state["pickup_datetime"],
        st.session_state["pickup_longitude"],
        st.session_state["pickup_latitude"],
        st.session_state["dropoff_longitude"],
        st.session_state["dropoff_latitude"],
        st.session_state["passenger_count"],
    )

    with st.spinner("🤖 calling the model..."):
        fare = call_fare_api(API_URL, params)
        time.sleep(0.3)

    st.success("✅ prediction ready")
    st.metric("💸 fare ($)", f"{fare:.2f}")

st.divider()
st.caption("💡 la carte suit les routes via OSRM. pour éviter de spammer OSRM, le routing est caché 60s (ttl).")
