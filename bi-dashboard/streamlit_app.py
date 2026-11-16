
from pathlib import Path

from utils import data

import streamlit as st


st.set_page_config(
    page_title="PQ-BI",
    page_icon=":material/insights:",
    layout="wide",
)

# Hide only the Deploy button
st.markdown(
    """
    <style>
        /* Hide Deploy */
        [data-testid="stAppDeployButton"] {
            display: none !important;
        }
        /* Hide Rerun / Always rerun */
        [data-testid="stStatusWidget"] {
            display: none !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)



STATIC = Path(__file__).parent / "static"
logo_variant = "dark" if st.context.theme.type == "dark" else "light"
st.logo(
    STATIC / f"logo-{logo_variant}.svg", icon_image=STATIC / "ruaLogo.svg", size="large"
)

page = st.navigation(
    [
        st.Page(
            "app_pages/overview.py",
            title="Overview",
            icon=":material/insights:",
            default=True,
        ),
        st.Page("app_pages/accounts.py", title="Accounts", icon=":material/groups:"),
        st.Page(
            "app_pages/pipeline.py", title="Pipeline", icon=":material/filter_alt:"
        ),
    ],
    position="top",
)


def reset_filters() -> None:
    # Bound widgets are reset by assigning their keys in a callback.
    st.session_state.period = data.DEFAULT_PERIOD
    st.session_state.regions = []
    st.session_state.plans = []
    st.session_state.annotations = False


# The entrypoint draws the page title and the global filters, so every page
# shares them. The filter summary is filled in once the widgets have run.
with st.container(horizontal=True, vertical_alignment="center"):
    with st.container(gap=None):
        st.title(page.title, icon=page.icon, anchor=False)
        summary = st.empty()
    st.button(
        "Reset",
        icon=":material/restart_alt:",
        type="tertiary",
        on_click=reset_filters,
        help="Reset the period, filters, and annotations",
    )

with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
    st.segmented_control(
        "Period",
        list(data.PERIODS),
        default=data.DEFAULT_PERIOD,
        required=True,
        key="period",
        bind="query-params",
        label_visibility="collapsed",
    )
    with st.popover("Filters", icon=":material/tune:"):
        st.pills(
            "Regions",
            data.REGIONS,
            selection_mode="multi",
            key="regions",
            help="Leave empty to include all regions.",
            bind="query-params",
        )
        st.pills(
            "Plans",
            data.PLANS,
            selection_mode="multi",
            key="plans",
            help="Leave empty to include all plans.",
            bind="query-params",
        )
        st.caption("Filters are saved in the URL, so you can share the current view.")
    st.toggle(
        "Annotations",
        value=False,
        key="annotations",
        bind="query-params",
        help="Mark product and pricing milestones on time-series charts.",
    )

summary.caption(data.current_filters().describe())

page.run()
