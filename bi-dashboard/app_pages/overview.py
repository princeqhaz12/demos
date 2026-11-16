"""Revenue overview page.
Revenue KPIs and charts load concurrently, with the layout displayed first.
The main script displays section headers, card frames, titles, and skeleton
placeholders immediately. Parallel fragments then replace the skeletons as
their data becomes available.
The revenue-by-industry card uses Streamlit's native ECharts component.
Because the native component does not provide chart-click events, a selectbox
is used to filter the Top Accounts table.
"""
import streamlit as st
from utils import charts, data
from utils.components import (
    account_columns,
    account_table,
    card_header,
    card_menu,
    open_clicked_account,
    section_header,
)
from utils.definitions import DEFINITIONS
from utils.formatting import change, money, signed_pct, signed_pts
# -------------------------------------------------------------------
# Dashboard dimensions
# -------------------------------------------------------------------
# Each skeleton uses the height of the content that will replace it.
# This prevents the dashboard layout from moving while data loads.
KPI_HEIGHT = 186
CHART_HEIGHT = 320
USAGE_HEIGHT = 260
DRILLDOWN_HEIGHT = 444
# -------------------------------------------------------------------
# KPI configuration
# -------------------------------------------------------------------
KPIS = {
    "arr": (
        "Annual recurring revenue",
        ":material/payments:",
        "area",
    ),
    "net_new_mrr": (
        "Net new MRR",
        ":material/trending_up:",
        "bar",
    ),
    "nrr": (
        "Net revenue retention",
        ":material/autorenew:",
        "line",
    ),
    "gross_churn": (
        "Monthly gross churn",
        ":material/trending_down:",
        "bar",
    ),
}
# -------------------------------------------------------------------
# Current dashboard filters
# -------------------------------------------------------------------
filters = data.current_filters()
# -------------------------------------------------------------------
# CSV export
# -------------------------------------------------------------------
def export_csv() -> bytes:
    """Export the currently filtered accounts as CSV."""
    accounts, _ = data.load_book()
    filtered_accounts = data.filter_accounts(
        accounts,
        filters,
    )
    return data.accounts_csv(filtered_accounts)
# -------------------------------------------------------------------
# KPI card
# -------------------------------------------------------------------
@st.fragment(parallel=True)
def kpi_card(
    kpi: str,
    filters: data.Filters,
) -> None:
    """Display one certified revenue KPI."""
    accounts, history = data.load_book()
    filtered_accounts = data.filter_accounts(
        accounts,
        filters,
    )
    account_ids = filtered_accounts.index
    monthly_kpis = data.monthly_kpis(
        history,
        account_ids,
        filters.months,
    )
    series = monthly_kpis[kpi]
    if series.empty:
        st.warning(f"No data is available for {KPIS[kpi][0]}.")
        return
    first_value = series.iloc[0]
    last_value = series.iloc[-1]
    comparison_window = f"vs. {filters.months} months ago"
    if kpi == "arr":
        value = money(last_value)
        delta = signed_pct(
            change(
                last_value,
                first_value,
            )
        )
        description = comparison_window
    elif kpi == "net_new_mrr":
        comparison_values = series.iloc[1:-1]
        if comparison_values.empty:
            period_average = series.mean()
        else:
            period_average = comparison_values.mean()
        value = money(last_value)
        delta = signed_pct(
            change(
                last_value,
                period_average,
            )
        )
        description = "vs. period average"
    elif kpi == "nrr":
        value = f"{last_value:.1f}%"
        delta = signed_pts(
            last_value - first_value
        )
        description = comparison_window
    else:
        comparison_values = series.iloc[1:]
        if comparison_values.empty:
            period_average = series.mean()
        else:
            period_average = comparison_values.mean()
        value = f"{last_value:.1f}%"
        delta = signed_pts(
            last_value - period_average
        )
        description = "vs. period average"
    label, icon, chart_type = KPIS[kpi]
    sparkline_data = series.iloc[1:]
    if sparkline_data.empty:
        sparkline_data = series
    st.metric(
        label=f"{label} :green[:material/verified:]",
        value=value,
        delta=delta,
        delta_color=(
            "inverse"
            if kpi == "gross_churn"
            else "normal"
        ),
        delta_description=description,
        chart_data=sparkline_data,
        chart_type=chart_type,
        icon=icon,
        border=True,
        help=DEFINITIONS[kpi].measures,
        height=KPI_HEIGHT,
    )
# -------------------------------------------------------------------
# MRR by plan
# -------------------------------------------------------------------
@st.fragment(parallel=True)
def mrr_growth_card(
    filters: data.Filters,
) -> None:
    """Display monthly recurring revenue by plan."""
    with st.container(
        border=True,
        height="stretch",
    ):
        controls = card_header(
            "MRR by plan",
            "Monthly recurring revenue, stacked by plan",
            certified=True,
        )
        view = controls.segmented_control(
            "View",
            ["$", "%"],
            default="$",
            required=True,
            key="growth_view",
            label_visibility="collapsed",
            help="Show absolute MRR or each plan's share",
        )
        card_menu(
            controls,
            "mrr_by_plan",
            {
                "mrr_forecast": "forecast",
                "mrr_compare": "last year",
            },
        )
        with st.skeleton(height=CHART_HEIGHT):
            accounts, history = data.load_book()
            region_accounts = accounts[
                accounts["region"].isin(filters.regions)
            ]
            monthly = data.mrr_by_plan(
                history,
                region_accounts,
                filters.months,
            )
            year_earlier = None
            if st.session_state.get(
                "mrr_compare",
                False,
            ):
                year_earlier = data.mrr_by_plan(
                    history,
                    region_accounts,
                    filters.months,
                    years_back=1,
                )
            forecast = None
            if st.session_state.get(
                "mrr_forecast",
                False,
            ):
                forecast = data.mrr_forecast(monthly)
            chart_options = charts.mrr_growth(
                monthly,
                filters.plans,
                share=view == "%",
                forecast=forecast,
                year_earlier=year_earlier,
                milestones=data.milestones(filters),
            )
            st.echarts_chart(
                chart_options,
                height=CHART_HEIGHT,
                key="mrr_growth_chart",
                alt=(
                    "Monthly recurring revenue by plan over time; "
                    "Enterprise contributes most"
                ),
            )
# -------------------------------------------------------------------
# MRR bridge
# -------------------------------------------------------------------
@st.fragment(parallel=True)
def mrr_bridge_chart(
    filters: data.Filters,
) -> None:
    """Display MRR movement over the selected period."""
    accounts, history = data.load_book()
    filtered_accounts = data.filter_accounts(
        accounts,
        filters,
    )
    account_ids = filtered_accounts.index
    movements = data.mrr_movements(
        history,
        account_ids,
        filters.months,
    )
    chart_options = charts.mrr_bridge(movements)
    st.echarts_chart(
        chart_options,
        height=CHART_HEIGHT,
        key="mrr_bridge_chart",
        alt=(
            f"MRR grew from {money(movements['start'])} "
            f"to {money(movements['end'])}, mostly from expansion"
        ),
    )
# -------------------------------------------------------------------
# Product usage heatmap
# -------------------------------------------------------------------
@st.fragment(parallel=True)
def usage_chart(
    filters: data.Filters,
) -> None:
    """Display product sessions by weekday and UTC hour."""
    usage_data = data.load_usage()
    usage_matrix = data.usage_matrix(
        usage_data,
        filters.regions,
    )
    chart_options = charts.usage_heatmap(
        usage_matrix
    )
    st.echarts_chart(
        chart_options,
        height=USAGE_HEIGHT,
        key="usage_heatmap_chart",
        alt=(
            "Product sessions by weekday and UTC hour, "
            "busiest on weekday afternoons"
        ),
    )
# -------------------------------------------------------------------
# Industry drilldown and top accounts
# -------------------------------------------------------------------
@st.fragment
def industry_drilldown(
    filters: data.Filters,
) -> None:
    """Display revenue by industry and the filtered top accounts.
    A native Streamlit selectbox is used for filtering. This avoids the
    streamlit-echarts BidiComponent error and ensures that changing the
    industry reruns only this fragment.
    """
    accounts, _ = data.load_book()
    filtered_accounts = data.filter_accounts(
        accounts,
        filters,
    )
    active_accounts = filtered_accounts[
        filtered_accounts["mrr"] > 0
    ].copy()
    revenue_by_industry = (
        active_accounts
        .groupby("industry")["mrr"]
        .sum()
        .reindex(
            data.INDUSTRIES,
            fill_value=0,
        )
    )
    industry_column, accounts_column = st.columns(
        [2, 3]
    )
    # ---------------------------------------------------------------
    # Industry chart
    # ---------------------------------------------------------------
    with industry_column.container(
        border=True,
        height="stretch",
    ):
        controls = card_header(
            "Revenue by industry",
            "Choose an industry to filter the accounts",
            certified=True,
        )
        card_menu(
            controls,
            "industry_mix",
        )
        available_industries = [
            industry
            for industry in data.INDUSTRIES
            if revenue_by_industry.get(industry, 0) > 0
        ]
        industry_options = [
            "All industries",
            *available_industries,
        ]
        selected_option = st.selectbox(
            "Filter by industry",
            options=industry_options,
            index=0,
            key="industry_filter",
            help=(
                "Select an industry to filter the Top Accounts table."
            ),
        )
        if selected_option == "All industries":
            selected_industry = None
        else:
            selected_industry = selected_option
        industry_chart_options = charts.industry_mix(
            revenue_by_industry
        )
        st.echarts_chart(
            industry_chart_options,
            height=CHART_HEIGHT + 40,
            key="industry_mix_chart",
            alt="Share of monthly recurring revenue by industry",
        )
    # ---------------------------------------------------------------
    # Filter top accounts
    # ---------------------------------------------------------------
    if selected_industry:
        top_accounts = active_accounts[
            active_accounts["industry"] == selected_industry
        ].copy()
    else:
        top_accounts = active_accounts.copy()
    top_accounts = top_accounts.nlargest(
        10,
        "mrr",
    )
    # ---------------------------------------------------------------
    # Top accounts table
    # ---------------------------------------------------------------
    with accounts_column.container(
        border=True,
        height="stretch",
    ):
        if selected_industry:
            table_description = (
                f"{selected_industry} customers by MRR"
            )
        else:
            table_description = "Largest customers by MRR"
        controls = card_header(
            "Top accounts",
            table_description,
        )
        if selected_industry:
            controls.badge(
                selected_industry,
                icon=":material/filter_alt:",
                color="primary",
            )
        if top_accounts.empty:
            st.info(
                "No active accounts are available for this industry."
            )
        else:
            account_table_data = account_table(
                top_accounts
            )
            st.dataframe(
                account_table_data,
                column_config=account_columns(
                    compact=True,
                    key="top_accounts_click",
                ),
                hide_index=True,
                height=CHART_HEIGHT + 40,
            )
            open_clicked_account(
                account_table_data,
                "top_accounts_click",
            )
# ===================================================================
# PAGE LAYOUT
# ===================================================================
# -------------------------------------------------------------------
# Revenue section header
# -------------------------------------------------------------------
actions = section_header(
    "Revenue",
    help=(
        "Certified metrics, owned by revenue operations "
        "and refreshed hourly."
    ),
    sql="revenue",
)
actions.badge(
    "Live",
    icon=":material/radio_button_checked:",
    color="green",
)
actions.download_button(
    "Export",
    export_csv,
    file_name="nimbus_accounts.csv",
    mime="text/csv",
    icon=":material/download:",
    on_click="ignore",
)
# -------------------------------------------------------------------
# KPI row
# -------------------------------------------------------------------
# The main script draws the skeletons immediately. Each KPI fragment
# replaces its skeleton after the required data finishes loading.
with st.container(horizontal=True):
    for kpi_name in KPIS:
        with st.skeleton(height=KPI_HEIGHT):
            kpi_card(
                kpi_name,
                filters,
            )
# -------------------------------------------------------------------
# MRR growth and bridge row
# -------------------------------------------------------------------
growth_column, bridge_column = st.columns(
    [3, 2]
)
with growth_column:
    mrr_growth_card(filters)
with bridge_column.container(
    border=True,
    height="stretch",
):
    controls = card_header(
        "MRR bridge",
        f"How MRR moved over the last {filters.months} months",
        certified=True,
    )
    card_menu(
        controls,
        "mrr_bridge",
    )
    with st.skeleton(height=CHART_HEIGHT):
        mrr_bridge_chart(filters)
# -------------------------------------------------------------------
# Usage heatmap
# -------------------------------------------------------------------
with st.container(border=True):
    controls = card_header(
        "When customers use Nimbus",
        (
            "Product sessions by weekday and hour (UTC) "
            "— shifts with the region filter"
        ),
        certified=True,
    )
    card_menu(
        controls,
        "usage",
    )
    with st.skeleton(height=USAGE_HEIGHT):
        usage_chart(filters)
# -------------------------------------------------------------------
# Industry drilldown
# -------------------------------------------------------------------
# The regular fragment comes last because it runs in the main script.
# All parallel fragments above start before this section loads.
with st.skeleton(height=DRILLDOWN_HEIGHT):
    industry_drilldown(filters)