import time
from datetime import datetime

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="🚕 Taxi Fare Predictor", page_icon="🚕", layout="centered")

st.title("🚕 taxi fare predictor")
st.caption("entre un trajet, clique sur **save** et je te sors une estimation + la map 🗺️")

API_URL = "https://wagon-data-tpl-image-129712465951.europe-west1.run.app/predict"
BASEMAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"


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


def call_api(url: str, params: dict) -> float:
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return float(data["fare"])


def make_map(
    pickup_longitude: float,
    pickup_latitude: float,
    dropoff_longitude: float,
    dropoff_latitude: float,
) -> pdk.Deck:
    points_df = pd.DataFrame(
        [
            {"type": "pickup 📍", "lat": pickup_latitude, "lon": pickup_longitude},
            {"type": "dropoff 🏁", "lat": dropoff_latitude, "lon": dropoff_longitude},
        ]
    )

    line_df = pd.DataFrame(
        [
            {
                "start_lat": pickup_latitude,
                "start_lon": pickup_longitude,
                "end_lat": dropoff_latitude,
                "end_lon": dropoff_longitude,
            }
        ]
    )

    center_lat = (pickup_latitude + dropoff_latitude) / 2
    center_lon = (pickup_longitude + dropoff_longitude) / 2

    layers = [
        pdk.Layer(
            "ScatterplotLayer",
            data=points_df,
            get_position="[lon, lat]",
            get_radius=80,
            pickable=True,
        ),
        pdk.Layer(
            "LineLayer",
            data=line_df,
            get_source_position="[start_lon, start_lat]",
            get_target_position="[end_lon, end_lat]",
            get_width=6,
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
# UI
# -----------------------------
with st.form("ride_form"):
    st.subheader("🧾 ride parameters")

    row0 = st.columns(1)
    pickup_datetime = row0[0].datetime_input("🕒 date & time")

    row1 = st.columns(2)
    pickup_longitude = row1[0].number_input(
        "📍 pickup longitude", value=-73.950655, format="%.6f", step=0.000001
    )
    pickup_latitude = row1[1].number_input(
        "📍 pickup latitude", value=40.783282, format="%.6f", step=0.000001
    )

    row2 = st.columns(2)
    dropoff_longitude = row2[0].number_input(
        "🏁 dropoff longitude", value=-73.984365, format="%.6f", step=0.000001
    )
    dropoff_latitude = row2[1].number_input(
        "🏁 dropoff latitude", value=40.769802, format="%.6f", step=0.000001
    )

    row3 = st.columns(1)
    passenger_count = row3[0].number_input(
        "👥 passenger count", min_value=1, max_value=8, value=2, step=1, format="%d"
    )

    submitted = st.form_submit_button("🚀 save & predict")


# -----------------------------
# Prediction + Map (only after submit)
# -----------------------------
if submitted:
    params = build_params(
        pickup_datetime,
        pickup_longitude,
        pickup_latitude,
        dropoff_longitude,
        dropoff_latitude,
        passenger_count,
    )

    with st.spinner("🤖 calling the model..."):
        fare = call_api(API_URL, params)
        time.sleep(0.5)

    st.success("✅ prediction ready")
    st.metric("💸 fare ($)", f"{fare:.2f}")

    st.subheader("🗺️ route preview")
    deck = make_map(
        pickup_longitude,
        pickup_latitude,
        dropoff_longitude,
        dropoff_latitude,
    )
    st.pydeck_chart(deck, use_container_width=True)

    with st.expander("🔎 debug (params sent to the API)"):
        st.write(params)

st.divider()
st.caption("💡 tip: change the coordinates to see the route update. no model file here, just an API call ✨")
