"""Streamlit app: a Run page to start sessions and a History page to follow them.

Launch with `make run`. The sessions and inputs folders come from the
`AURORA_SESSIONS_DIR` and `AURORA_INPUTS_DIR` environment variables.
"""

import os
import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path

import pandas as pd
import streamlit as st

from aurora_er.attachments import MARKETS, battery_template, prices_template
from aurora_er.dto import InvalidDTOError
from aurora_er.example import BATTERY_FILE as EXAMPLE_BATTERY_FILE
from aurora_er.example import PRICES_FILE as EXAMPLE_PRICES_FILE
from aurora_er.example import example_config
from aurora_er.loading import InputFileError, PriceSheet, price_sheets
from aurora_er.report import market_totals
from aurora_er.sessions import (
    SessionState,
    SessionStore,
    SessionSummary,
    launch,
    new_session_id,
    rerun,
    run_in_background,
    validation_errors,
)
from aurora_er.solver import HighsBackend, WindowSize
from aurora_er.ui.form import (
    BATTERY_FILE,
    PRICES_FILE,
    STEP_CHOICES,
    MarketChoice,
    RunForm,
    config_in,
    form_from_config,
    missing_fields,
    utc_datetime,
)

SESSIONS_DIR_VARIABLE = "AURORA_SESSIONS_DIR"
INPUTS_DIR_VARIABLE = "AURORA_INPUTS_DIR"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FILES = {BATTERY_FILE: "battery parameters spreadsheet", PRICES_FILE: "market prices spreadsheet"}
HELP = {
    "fill_example": (
        "Uses the provided Attachment 1 and Attachment 2 and the example run values: "
        "an empty new battery, 2018 to 2020, monthly windows."
    ),
    "battery_template": "Workbook with every battery parameter and its unit; fill in **Values**.",
    "prices_template": "Workbook with one sheet per example market and the expected headers.",
    "stored": (
        "Energy in the battery at the horizon start, in MWh. It must fit in the usable "
        "volume: the maximum storage volume reduced by degradation from the cycles used."
    ),
    "cycles": (
        "Full-cycle equivalents the battery has already done. One cycle is discharging the "
        "whole storage volume, in any number of steps. Cycles reduce the usable volume and "
        "count towards the lifetime limit."
    ),
    "commissioned": (
        "When the installed battery was put into service, in UTC. It must be at or before "
        "the horizon start and the battery must still be within its calendar lifetime. If "
        "it equals the horizon start, the purchase (capex) is counted in the result."
    ),
    "start": (
        "First instant optimised, in UTC (inclusive). It must fall on a step boundary of "
        "every market and inside the prices."
    ),
    "end": (
        "End of the optimised period, in UTC (exclusive). It must fall on a step boundary "
        "of every market and inside the prices."
    ),
    "window": (
        "The horizon is solved in consecutive windows, each starting from the previous "
        "one's battery state. Day and week windows are 24 hours and 7 days from the start; "
        "month follows calendar months. Shorter windows solve faster but see "
        "less of the prices ahead."
    ),
    "step": (
        "Duration of one row in that sheet. Capacity is committed to a market for a whole "
        "step. The file does not say it, so choose it here."
    ),
    "pace": (
        "Caps the cycles in each window to the remaining lifetime cycles spread evenly "
        "over the remaining calendar life. Usually not needed: each cycle already costs "
        "capex ÷ lifetime cycles."
    ),
    "limit": (
        "Maximum solver time per window, in seconds. If it is reached, the best plan found "
        "so far is kept and the window is marked feasible instead of optimal."
    ),
    "gap": (
        "How far from the best possible profit the solver may stop, as a fraction: 0.01 "
        "means within 1%. 0 solves each window to proven optimality."
    ),
    "run": (
        "Checks the spreadsheets and the form, then starts the run in the background "
        "and opens History."
    ),
    "refresh": "Reload the sessions and their statuses.",
}
PROTOTYPE_NOTICE = (
    "This is a prototype for running the battery dispatch model easily. Runs happen in "
    "the background while this app is open: stopping the app stops any running "
    "sessions, and they show as interrupted next time."
)
RUN_PAGE = "Run"
HISTORY_PAGE = "History"
BATTERY_HELP = (
    "One sheet named **Data** with a row per parameter: the parameter name in the first "
    "column, then **Values** and **Units**. Units must match the template "
    "(MW, MWh, -, years, cycles, %/cycle, £, £/year)."
)
PRICES_HELP = (
    "One sheet per market. In each sheet:\n\n"
    "- **Column A:** timestamps in UTC, one row per interval, consecutive with no gaps.\n"
    "- **Column B:** the price in £/MWh, used for buying and selling; its header names "
    'the market, e.g. "Market 1 Price [£/MWh]".\n\n'
    "After uploading, choose each sheet's step (15 min, 30 min or 1 hour) in the table "
    "below. Download the prices template for an example."
)


@st.cache_resource
def _mark_interrupted_once(sessions_dir: str) -> tuple[str, ...]:
    return SessionStore(Path(sessions_dir)).mark_interrupted()


def _start(store: SessionStore, session_id: str) -> None:
    run_in_background(store, session_id, HighsBackend())


def _init_state() -> None:
    """Set every widget's starting value once; widgets themselves take no `value=`."""
    if "upload_dir" not in st.session_state:
        st.session_state.upload_dir = Path(tempfile.mkdtemp(prefix="aurora-upload-"))
    st.session_state.setdefault("page", RUN_PAGE)
    if st.session_state.pop("open_history", False):
        st.session_state.page = HISTORY_PAGE
    st.session_state.setdefault("price_sheets", ())
    st.session_state.setdefault("selected_session", None)
    st.session_state.setdefault("sources", {})
    st.session_state.setdefault("uploader_round", 0)
    st.session_state.setdefault("stored", 0.0)
    st.session_state.setdefault("cycles", 0.0)
    for key in ("commissioned", "start", "end"):
        st.session_state.setdefault(f"{key}_date", None)
        st.session_state.setdefault(f"{key}_time", None)
    st.session_state.setdefault("window", None)
    st.session_state.setdefault("pace", False)
    st.session_state.setdefault("limit", 120.0)
    st.session_state.setdefault("gap", 0.0)


def _upload_dir() -> Path:
    folder: Path = st.session_state.upload_dir
    return folder


def _fill_with_example(inputs_dir: Path, upload_dir: Path) -> None:
    shutil.copy(inputs_dir / EXAMPLE_BATTERY_FILE, upload_dir / BATTERY_FILE)
    shutil.copy(inputs_dir / EXAMPLE_PRICES_FILE, upload_dir / PRICES_FILE)
    st.session_state.sources = {
        BATTERY_FILE: f"{EXAMPLE_BATTERY_FILE} (example)",
        PRICES_FILE: f"{EXAMPLE_PRICES_FILE} (example)",
    }
    st.session_state.uploader_round += 1
    _set_price_sheets(
        tuple(
            PriceSheet(sheet=market.sheet, price_column=market.price_column) for market in MARKETS
        )
    )
    for market in MARKETS:
        st.session_state[_step_key(market.sheet)] = market.step_length
    form = form_from_config(example_config(inputs_dir))
    _set_datetime("commissioned", form.commissioned_at)
    _set_datetime("start", form.start)
    _set_datetime("end", form.end)
    st.session_state.stored = form.stored_energy_mwh
    st.session_state.cycles = form.cycles_used
    st.session_state.window = form.window_size.value if form.window_size else None
    st.session_state.pace = form.enforce_cycle_pace
    st.session_state.limit = form.time_limit_seconds
    st.session_state.gap = form.mip_gap
    st.session_state.run_message = (
        "info",
        "Filled with the provided attachments and the example run values. "
        "Change anything before running.",
    )


def _step_key(sheet: str) -> str:
    return f"step::{sheet}"


def _step_label(step: timedelta | None) -> str:
    return "Choose" if step is None else STEP_CHOICES[step]


def _set_price_sheets(sheets: tuple[PriceSheet, ...]) -> None:
    st.session_state.price_sheets = sheets
    for sheet in sheets:
        st.session_state[_step_key(sheet.sheet)] = None


def _set_datetime(key: str, value: datetime | None) -> None:
    st.session_state[f"{key}_date"] = value.date() if value else None
    st.session_state[f"{key}_time"] = value.timetz().replace(tzinfo=None) if value else None


def _datetime_input(label: str, key: str) -> datetime | None:
    st.markdown(label, help=HELP[key])
    day_column, time_column = st.columns(2)
    day = day_column.date_input(f"{label} date", key=f"{key}_date", label_visibility="collapsed")
    clock = time_column.time_input(f"{label} time", key=f"{key}_time", label_visibility="collapsed")
    return utc_datetime(day, clock)


def _file_input(label: str, file_name: str, upload_dir: Path, help_text: str) -> None:
    uploaded = st.file_uploader(
        label,
        type=["xlsx"],
        key=f"{file_name}_{st.session_state.uploader_round}",
        help=help_text,
    )
    if uploaded is not None and st.session_state.sources.get(file_name) != uploaded.name:
        (upload_dir / file_name).write_bytes(uploaded.getvalue())
        st.session_state.sources[file_name] = uploaded.name
        if file_name == PRICES_FILE:
            try:
                _set_price_sheets(price_sheets(upload_dir / PRICES_FILE))
            except InputFileError as error:
                _set_price_sheets(())
                st.error(str(error))
    if file_name in st.session_state.sources:
        st.caption(f"Using {st.session_state.sources[file_name]}")


def _market_steps() -> tuple[MarketChoice, ...]:
    sheets: tuple[PriceSheet, ...] = st.session_state.price_sheets
    if not sheets:
        return ()
    st.markdown("**Markets found in the prices spreadsheet**")
    with st.container(border=True):
        sheet_header, column_header, step_header = st.columns([2, 3, 2])
        sheet_header.caption("Sheet")
        column_header.caption("Price column")
        step_header.caption("Step", help=HELP["step"])
        choices = []
        for sheet in sheets:
            sheet_cell, column_cell, step_cell = st.columns([2, 3, 2], vertical_alignment="center")
            sheet_cell.write(sheet.sheet)
            column_cell.write(sheet.price_column)
            step = step_cell.selectbox(
                f"Step for {sheet.sheet}",
                [None, *STEP_CHOICES],
                format_func=_step_label,
                key=_step_key(sheet.sheet),
                help=HELP["step"],
                label_visibility="collapsed",
            )
            choices.append(
                MarketChoice(sheet=sheet.sheet, price_column=sheet.price_column, step_length=step)
            )
    return tuple(choices)


def _run_page(store: SessionStore, inputs_dir: Path) -> None:
    upload_dir = _upload_dir()
    run_slot = st.container(horizontal=True, horizontal_alignment="right")
    message_slot = st.container()
    st.button(
        "Fill with example",
        help=HELP["fill_example"],
        icon=":material/auto_fix_high:",
        on_click=_fill_with_example,
        args=(inputs_dir, upload_dir),
    )
    with st.container(horizontal=True):
        st.download_button(
            "Download battery template",
            battery_template(),
            help=HELP["battery_template"],
            icon=":material/download:",
            file_name="battery-template.xlsx",
            mime=XLSX_TYPE,
        )
        st.download_button(
            "Download prices template",
            prices_template(),
            help=HELP["prices_template"],
            icon=":material/download:",
            file_name="prices-template.xlsx",
            mime=XLSX_TYPE,
        )

    files_column, battery_column = st.columns(2)
    with files_column:
        st.subheader("Spreadsheets")
        _file_input("Battery parameters", BATTERY_FILE, upload_dir, BATTERY_HELP)
        _file_input("Market prices", PRICES_FILE, upload_dir, PRICES_HELP)
        markets = _market_steps()
    with battery_column:
        st.subheader("Battery state at the start")
        stored = st.number_input(
            "Stored energy (MWh)", min_value=0.0, key="stored", help=HELP["stored"]
        )
        cycles = st.number_input("Cycles used", min_value=0.0, key="cycles", help=HELP["cycles"])
        commissioned_at = _datetime_input("Commissioned at (UTC)", "commissioned")

    horizon_column, solver_column = st.columns(2)
    with horizon_column:
        st.subheader("Horizon")
        start = _datetime_input("Start (UTC)", "start")
        end = _datetime_input("End (UTC, exclusive)", "end")
        window = st.segmented_control(
            "Window size",
            [size.value for size in WindowSize],
            key="window",
            help=HELP["window"],
        )
        st.caption(
            "The horizon is solved window by window; each starts from the previous "
            "one's battery state."
        )
    with solver_column:
        st.subheader("Solver")
        pace = st.checkbox("Enforce cycle pace", key="pace", help=HELP["pace"])
        limit = st.number_input(
            "Time limit per window (s)", min_value=1.0, key="limit", help=HELP["limit"]
        )
        gap = st.number_input(
            "MIP gap",
            min_value=0.0,
            max_value=0.999,
            format="%.3f",
            key="gap",
            help=HELP["gap"],
        )

    form = RunForm(
        stored_energy_mwh=stored,
        cycles_used=cycles,
        commissioned_at=commissioned_at,
        start=start,
        end=end,
        window_size=WindowSize(window) if window else None,
        enforce_cycle_pace=pace,
        time_limit_seconds=limit,
        mip_gap=gap,
        markets=markets,
    )
    with run_slot:
        if st.button("Run", type="primary", icon=":material/play_arrow:", help=HELP["run"]):
            _run(store, form, upload_dir)
    if "run_message" in st.session_state:
        kind, text = st.session_state.run_message
        with message_slot:
            getattr(st, kind)(text)


def _run(store: SessionStore, form: RunForm, upload_dir: Path) -> None:
    present = {name: (upload_dir / name).exists() for name in FILES}
    missing = missing_fields(form, {FILES[name]: present[name] for name in FILES})
    if missing:
        st.session_state.run_message = (
            "error",
            "Fix these before running:\n\n- " + "\n- ".join(missing),
        )
        return
    try:
        errors = validation_errors(config_in(form, upload_dir))
    except InvalidDTOError as error:
        errors = (str(error),)
    if errors:
        st.session_state.run_message = (
            "error",
            "Fix these before running:\n\n- " + "\n- ".join(errors),
        )
        return
    session_id = new_session_id(datetime.now(UTC))
    launch(
        store,
        session_id,
        {name: upload_dir / name for name in FILES},
        partial(config_in, form),
        partial(_start, store),
    )
    st.session_state.sources = {}
    st.session_state.uploader_round += 1
    _set_price_sheets(())
    st.session_state.selected_session = session_id
    st.session_state.pop("run_message", None)
    st.session_state.history_message = f"Session {session_id} started."
    st.session_state.open_history = True
    st.rerun()


def _select_session(session_id: str) -> None:
    st.session_state.selected_session = session_id


def _history_page(store: SessionStore) -> None:
    if "history_message" in st.session_state:
        st.success(st.session_state.pop("history_message"))
    sessions = store.list()
    if not sessions:
        st.button("Refresh", icon=":material/refresh:", help=HELP["refresh"])
        st.info("No runs yet. Start one from the Run page.")
        return
    by_id = {summary.session_id: summary for summary in sessions}
    if st.session_state.selected_session not in by_id:
        st.session_state.selected_session = sessions[0].session_id
    list_column, detail_column = st.columns([1, 2], gap="large")
    with list_column:
        st.button("Refresh", icon=":material/refresh:", help=HELP["refresh"])
        st.caption("Sessions, newest first")
        for summary in sessions:
            st.button(
                f"{summary.created_at:%Y-%m-%d %H:%M:%S} · {summary.status.state.value}",
                key=f"session::{summary.session_id}",
                type=(
                    "primary"
                    if summary.session_id == st.session_state.selected_session
                    else "secondary"
                ),
                width="stretch",
                on_click=_select_session,
                args=(summary.session_id,),
            )
    with detail_column:
        _session_detail(store, by_id[st.session_state.selected_session])


def _session_detail(store: SessionStore, summary: SessionSummary) -> None:
    session_id = summary.session_id
    st.subheader(f"{summary.created_at:%Y-%m-%d %H:%M:%S} UTC")
    try:
        config = store.read_config(session_id)
    except (OSError, KeyError, ValueError) as error:
        st.error(
            f"This session's settings cannot be read, e.g. because they use an option "
            f"that no longer exists: {error}"
        )
        return
    st.caption(
        f"{config.horizon.start:%Y-%m-%d} → {config.horizon.end:%Y-%m-%d} "
        f"· {config.window_size.value} windows · {summary.status.state.value}"
    )
    state = summary.status.state
    if state is SessionState.RUNNING:
        if store.cancel_requested(session_id):
            st.info("Cancel requested. The run stops after the current window.")
        else:
            st.info("Solving. The result appears here when the status changes to done.")
            if st.button("Cancel"):
                store.request_cancel(session_id)
                st.rerun()
        return
    if st.button("Rerun"):
        new_id = new_session_id(datetime.now(UTC))
        rerun(store, session_id, new_id, partial(_start, store))
        st.session_state.selected_session = new_id
        st.success(f"Session {new_id} started. Refresh to follow it.")
    if state is SessionState.DONE:
        _result(store, session_id)
    elif state is SessionState.ERROR:
        st.error(summary.status.detail)
    else:
        st.info(summary.status.detail)


def _result(store: SessionStore, session_id: str) -> None:
    session_result = store.read_result(session_id)
    result = session_result.result
    windows = result.windows
    metrics = st.columns(4)
    metrics[0].metric(
        "Market profit",
        f"£{result.market_profit_gbp:,.2f}",
        help=f"{len(windows)} windows, "
        + ("all optimal" if result.all_optimal else "some stopped at the time limit"),
    )
    metrics[1].metric("Net profit", f"£{result.net_profit_gbp:,.2f}")
    metrics[2].metric("Cycles used", f"{result.cycles_used_in_horizon:,.2f}")
    metrics[3].metric("Replacements", result.replacements)
    st.markdown("**Market profit per window**")
    st.bar_chart(
        pd.DataFrame(
            {"Market profit (£)": [window.market_profit_gbp for window in windows]},
            index=[window.horizon.start.strftime("%Y-%m-%d") for window in windows],
        )
    )
    markets_column, money_column = st.columns(2)
    markets_column.dataframe(
        pd.DataFrame(
            market_totals(result),
            columns=["Market", "Charged MWh", "Discharged MWh", "Profit £"],
        ),
        hide_index=True,
    )
    money_column.dataframe(
        pd.DataFrame(
            {
                "": ["Market profit", "Capex", "Opex", "Battery value change", "Net profit"],
                "£": [
                    result.market_profit_gbp,
                    -result.capex_gbp,
                    -result.opex_gbp,
                    result.battery_value_end_gbp - result.battery_value_start_gbp,
                    result.net_profit_gbp,
                ],
            }
        ),
        hide_index=True,
    )
    with st.expander(f"Windows ({len(windows)})"):
        st.dataframe(
            pd.DataFrame(
                {
                    "Window": [window.horizon.start.strftime("%Y-%m-%d") for window in windows],
                    "Status": [window.status.value for window in windows],
                    "Market profit £": [window.market_profit_gbp for window in windows],
                    "Cycles": [window.cycles_used_in_horizon for window in windows],
                }
            ),
            hide_index=True,
        )
    if session_result.warnings:
        st.warning("\n".join(session_result.warnings))


def main() -> None:
    """Render the app."""
    st.set_page_config(page_title="Battery dispatch", layout="wide")
    st.title("Battery dispatch")
    st.caption("Two-market battery arbitrage, solved in rolling windows")
    st.info(PROTOTYPE_NOTICE, icon=":material/science:")
    sessions_dir = os.environ.get(SESSIONS_DIR_VARIABLE)
    inputs_dir = os.environ.get(INPUTS_DIR_VARIABLE)
    if sessions_dir is None or inputs_dir is None:
        st.error(f"Set {SESSIONS_DIR_VARIABLE} and {INPUTS_DIR_VARIABLE}; `make run` does this.")
        return
    _mark_interrupted_once(sessions_dir)
    _init_state()
    store = SessionStore(Path(sessions_dir))
    with st.container(horizontal=True, horizontal_alignment="center"):
        page = st.segmented_control(
            "Page",
            [RUN_PAGE, HISTORY_PAGE],
            required=True,
            key="page",
            label_visibility="collapsed",
        )
    if page == HISTORY_PAGE:
        _history_page(store)
    else:
        _run_page(store, Path(inputs_dir))


if __name__ == "__main__":
    main()
