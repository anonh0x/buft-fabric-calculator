import pandas as pd
import streamlit as st

st.set_page_config(page_title="Lay Weight and Waste Calculator", page_icon="🧵", layout="centered")
st.title("Lay Weight and Waste Calculator")
st.caption("Enter fabric and lay details to estimate fabric weight and cutting waste.")

COMPOSITIONS = {
    "100% cotton": 5,
    "Cotton / polyester": 3,
    "100% polyester": 1,
    "Viscose / rayon": 6,
    "Linen": 4,
    "Wool": 3,
    "Nylon": 2,
    "Cotton / elastane": 4,
    "Manual / other": None,
}
CUTTING_METHODS = {
    "Straight knife": 1.0,
    "Band knife": 0.8,
    "Round knife": 1.0,
    "Die cutting": 0.5,
    "CNC / auto cutter": 0.3,
    "Laser": 0.2,
}

# Fabric-length factor of each size relative to the base size (M = 1.00).
# These are starting values; they can be edited in the size table on the page.
LETTER_FACTORS = {
    "XS": 0.90, "S": 0.95, "M": 1.00, "L": 1.05,
    "XL": 1.10, "XXL": 1.15, "XXXL": 1.20,
}
NUMERIC_SIZES = [str(n) for n in range(0, 81, 2)]
SIZE_OPTIONS = list(LETTER_FACTORS) + NUMERIC_SIZES


def default_factor(size: str) -> float:
    """Default length factor for a size (numeric sizes: 40 = 1.00, +0.5% per size step)."""
    if size in LETTER_FACTORS:
        return LETTER_FACTORS[size]
    return 1 + (int(size) - 40) * 0.005


def inches(value: float, unit: str) -> float:
    """Convert a length to inches."""
    if unit == "yard":
        return value * 36
    if unit == "metre":
        return value / 0.0254
    if unit == "cm":
        return value / 2.54
    return value


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}"


tab_calc, tab_code = st.tabs(["🧮 Calculator", "🐍 Python Source Code"])

with tab_calc:
    st.header("Fabric")
    department = st.selectbox("Department", ["Mens", "Womens", "Kids wear"])
    gsm = st.number_input("GSM (g/m²)", min_value=0.0, value=180.0, step=1.0)
    width = st.number_input("Cuttable width", min_value=0.0, value=60.0, step=0.5)
    width_unit = st.selectbox("Width unit", ["inch", "cm"])
    composition = st.selectbox("Composition", list(COMPOSITIONS.keys()))
    manual_composition = ""
    if composition == "Manual / other":
        manual_composition = st.text_input("Enter composition", placeholder="e.g. 95% Cotton, 5% Elastane")

    default_shrink = COMPOSITIONS[composition]
    shrinkage = st.number_input(
        "Shrinkage (%)", min_value=0.0, max_value=99.9,
        value=float(default_shrink if default_shrink is not None else 0), step=0.5
    )

    st.header("Lay and cutting")

    # ---- Size set: now multi-select ------------------------------------------
    size_set = st.multiselect(
        "Size set (select one or more)",
        SIZE_OPTIONS,
        default=["M"],
    )

    size_multiplier = 1.0
    pieces_per_ply = 0
    if size_set:
        size_df = pd.DataFrame({
            "Size": size_set,
            "Pieces per marker": [1] * len(size_set),
            "Length factor": [round(default_factor(s), 3) for s in size_set],
        })
        edited = st.data_editor(
            size_df,
            hide_index=True,
            disabled=["Size"],
            key="size_table_" + "_".join(size_set),
            column_config={
                "Pieces per marker": st.column_config.NumberColumn(
                    "Pieces per marker", min_value=0, step=1,
                    help="How many garments of this size are in one marker.",
                ),
                "Length factor": st.column_config.NumberColumn(
                    "Length factor", min_value=0.1, step=0.01, format="%.3f",
                    help="Fabric length of this size relative to the base size (M = 1.00).",
                ),
            },
        )
        edited = edited.fillna(0)
        size_multiplier = float((edited["Pieces per marker"] * edited["Length factor"]).sum())
        pieces_per_ply = int(edited["Pieces per marker"].sum())

    scale_by_size = st.checkbox(
        "Scale spreading length by selected sizes",
        value=True,
        help="On: the length below is for ONE piece of the base size (M). "
             "The marker length = that length × (sum of pieces × length factor). "
             "Off: the length below is used as entered and sizes are only a label.",
    )

    spread_length = st.number_input(
        "Spreading length (1 piece, base size)" if scale_by_size else "Spreading length",
        min_value=0.0, value=96.0, step=1.0,
    )
    length_unit = st.selectbox("Spreading length unit", ["inch", "yard", "metre"])
    plies = st.number_input("Number of plies", min_value=1, value=100, step=1)
    efficiency = st.number_input("Marker efficiency (%)", min_value=1.0, max_value=100.0, value=85.0, step=0.5)
    cutting_method = st.selectbox("Cutting method", list(CUTTING_METHODS.keys()))
    cutting_loss = st.number_input(
        "Cutting loss (%)", min_value=0.0, value=CUTTING_METHODS[cutting_method], step=0.1
    )

    allowance_mode = st.selectbox(
        "Shrinkage allowance",
        ["Calculate from shrinkage %", "Enter my own allowance", "No allowance"],
    )
    allowance_value = 0.0
    allowance_unit = "%"
    if allowance_mode == "Enter my own allowance":
        allowance_value = st.number_input("Allowance added to each ply", min_value=0.0, value=0.0, step=0.1)
        allowance_unit = st.selectbox("Allowance unit", ["%", "inch", "cm"])

    # Convert inputs to a consistent unit system.
    width_m = width / 100 if width_unit == "cm" else width * 0.0254
    base_spread_inches = inches(spread_length, length_unit)
    spread_inches = base_spread_inches * size_multiplier if scale_by_size else base_spread_inches

    if allowance_mode == "Calculate from shrinkage %":
        adjusted_length_inches = spread_inches / (1 - shrinkage / 100)
    elif allowance_mode == "Enter my own allowance":
        if allowance_unit == "%":
            adjusted_length_inches = spread_inches * (1 + allowance_value / 100)
        elif allowance_unit == "cm":
            adjusted_length_inches = spread_inches + allowance_value / 2.54
        else:
            adjusted_length_inches = spread_inches + allowance_value
    else:
        adjusted_length_inches = spread_inches

    adjusted_length_m = adjusted_length_inches * 0.0254
    allowance_inches = adjusted_length_inches - spread_inches
    allowance_percent = (allowance_inches / spread_inches * 100) if spread_inches else 0.0

    st.header("Results")
    if not size_set:
        st.error("Select at least one size.")
    elif scale_by_size and size_multiplier <= 0:
        st.error("Set at least one piece (with a length factor above zero) in the size table.")
    elif gsm <= 0 or width <= 0 or spread_length <= 0:
        st.error("GSM, width, and spreading length must be greater than zero.")
    elif allowance_mode == "Calculate from shrinkage %" and shrinkage >= 100:
        st.error("Shrinkage must be below 100%.")
    else:
        weight_per_ply = gsm * width_m * adjusted_length_m / 1000
        total_weight = weight_per_ply * plies
        marker_loss_percent = 100 - efficiency
        total_waste_percent = marker_loss_percent + cutting_loss
        waste_weight = total_weight * total_waste_percent / 100
        usable_weight = total_weight - waste_weight
        marker_waste_kg = total_weight * marker_loss_percent / 100
        cutting_waste_kg = total_weight * cutting_loss / 100
        total_length_m = adjusted_length_m * plies
        total_pieces = pieces_per_ply * plies

        c1, c2 = st.columns(2)
        c1.metric("Actual fabric weight of total lay", f"{total_weight:,.2f} kg")
        c2.metric("Actual waste weight", f"{waste_weight:,.2f} kg")
        st.metric("Waste of total lay", f"{total_waste_percent:,.2f}%")

        st.subheader("Breakdown")
        if allowance_mode == "No allowance":
            allowance_text = "None"
        else:
            allowance_text = f"{allowance_percent:.2f}% · +{allowance_inches:.2f} in per ply"

        breakdown = {
            "Department": department,
            "Composition": manual_composition.strip() if composition == "Manual / other" and manual_composition.strip() else composition,
            "Size set": ", ".join(size_set),
            "Pieces per marker": f"{pieces_per_ply}" if pieces_per_ply else "—",
            "Size length multiplier": f"{size_multiplier:.3f}" if scale_by_size else "Not applied",
            "Marker length (before allowance)": f"{spread_inches:.2f} in",
            "Shrinkage allowance": allowance_text,
            "Length spread per ply": f"{adjusted_length_inches:.2f} in",
            "Weight per ply": f"{weight_per_ply:.3f} kg",
            "Total fabric length in lay": f"{total_length_m:.1f} m ({total_length_m / 0.9144:.1f} yd)",
            "Marker loss": f"{marker_loss_percent:.2f}% · {marker_waste_kg:.2f} kg",
            "Cutting loss": f"{cutting_loss:.2f}% · {cutting_waste_kg:.2f} kg",
            "Usable fabric weight": f"{usable_weight:.2f} kg",
        }
        if total_pieces > 0:
            breakdown["Total pieces in lay"] = f"{total_pieces:,}"
            breakdown["Fabric per piece (gross)"] = f"{total_weight / total_pieces:.3f} kg"
        st.table([{"Item": key, "Value": value} for key, value in breakdown.items()])

        st.caption(
            "Formula: marker length = base length × Σ(pieces × size length factor). "
            "Weight per ply (kg) = GSM × width (m) × adjusted length (m) ÷ 1000. "
            "Total lay weight = weight per ply × plies. Waste % = (100 − marker efficiency) + cutting loss %. "
            "These estimates depend on the accuracy of the inputs; compare cutting-loss assumptions with factory data."
        )

with tab_code:
    st.subheader("Python Source Code (`app.py`)")
    st.caption("This live web application is built with Python and Streamlit.")
    try:
        with open(__file__, "r", encoding="utf-8") as f:
            source_code = f.read()
        st.download_button(
            label="⬇️ Download Python File (app.py)",
            data=source_code,
            file_name="app.py",
            mime="text/x-python",
        )
        st.code(source_code, language="python", line_numbers=True)
    except Exception:
        st.info("Could not load source code.")
