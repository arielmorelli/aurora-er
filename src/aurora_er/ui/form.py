"""The Run form's values and how they become a `RunConfig`; no Streamlit here."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from aurora_er.attachments import PRICES_TIMEZONE, battery_sheet
from aurora_er.config import RunConfig
from aurora_er.dto import BatteryStateDTO, HorizonDTO, SolveOptionsDTO
from aurora_er.loading import MarketSheet
from aurora_er.solver import WindowSize

BATTERY_FILE = "battery.xlsx"
PRICES_FILE = "prices.xlsx"
STEP_CHOICES = {
    timedelta(minutes=15): "15 min",
    timedelta(minutes=30): "30 min",
    timedelta(hours=1): "1 hour",
}
PRICE_SUFFIX = " Price"


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketChoice:
    """One sheet of the prices spreadsheet and the step the user chose for it."""

    sheet: str
    """Sheet holding the market's prices."""

    price_column: str
    """Header of the price column, used for buying and selling."""

    step_length: timedelta | None
    """Duration of one row; `None` until the user chooses it."""


def market_name(choice: MarketChoice) -> str:
    """Name shown for a market: the price header before " Price", else the sheet name."""
    name, found, _ = choice.price_column.partition(PRICE_SUFFIX)
    return name if found and name else choice.sheet


@dataclass(frozen=True, slots=True, kw_only=True)
class RunForm:
    """Values entered in the Run tab; datetimes are UTC."""

    stored_energy_mwh: float
    """Energy in storage at the horizon start."""

    cycles_used: float
    """Cycles already used by the battery."""

    commissioned_at: datetime | None
    """When the battery was commissioned."""

    start: datetime | None
    """Horizon start."""

    end: datetime | None
    """Horizon end, exclusive."""

    window_size: WindowSize | None
    """How much of the horizon is solved at once."""

    enforce_cycle_pace: bool
    """Whether to cap cycles to the pace of the battery's lifetime."""

    time_limit_seconds: float
    """Solver time limit per window."""

    mip_gap: float
    """Relative optimality gap at which the solver may stop."""

    markets: tuple[MarketChoice, ...]
    """Sheets found in the prices spreadsheet, with their chosen steps."""


def utc_datetime(day: date | None, clock: time | None) -> datetime | None:
    """Combine a date and a time entered in UTC; `None` if either is missing."""
    if day is None or clock is None:
        return None
    return datetime.combine(day, clock, tzinfo=UTC)


def missing_fields(form: RunForm, files: Mapping[str, bool]) -> tuple[str, ...]:
    """What must still be provided before running, in the order shown on screen."""
    missing = [f"Upload the {name}." for name, present in files.items() if not present]
    if all(files.values()) and not form.markets:
        missing.append("The market prices spreadsheet has no sheet with timestamps and prices.")
    missing += [
        f'Choose the step for sheet "{market.sheet}".'
        for market in form.markets
        if market.step_length is None
    ]
    if form.commissioned_at is None:
        missing.append("Set when the battery was commissioned.")
    if form.start is None or form.end is None:
        missing.append("Set the horizon start and end.")
    if form.window_size is None:
        missing.append("Choose a window size.")
    return tuple(missing)


def config_in(form: RunForm, folder: Path) -> RunConfig:
    """Run config for the spreadsheets `battery.xlsx` and `prices.xlsx` in `folder`.

    Raises `ValueError` if the form is incomplete and `InvalidDTOError` if a value
    is out of range.
    """
    if (
        form.commissioned_at is None
        or form.start is None
        or form.end is None
        or form.window_size is None
        or not form.markets
        or any(market.step_length is None for market in form.markets)
    ):
        raise ValueError("the form is incomplete")
    return RunConfig(
        battery_sheet=battery_sheet(folder / BATTERY_FILE),
        battery_state=BatteryStateDTO(
            stored_energy_mwh=form.stored_energy_mwh,
            cycles_used=form.cycles_used,
            commissioned_at=form.commissioned_at,
        ),
        market_sheets=tuple(
            MarketSheet(
                name=market_name(market),
                path=folder / PRICES_FILE,
                sheet=market.sheet,
                buy_price_column=market.price_column,
                sell_price_column=market.price_column,
                timezone=PRICES_TIMEZONE,
                step_length=market.step_length,
            )
            for market in form.markets
            if market.step_length is not None
        ),
        horizon=HorizonDTO(start=form.start, end=form.end),
        window_size=form.window_size,
        options=SolveOptionsDTO(
            enforce_cycle_pace=form.enforce_cycle_pace,
            time_limit_seconds=form.time_limit_seconds,
            mip_gap=form.mip_gap,
        ),
    )


def form_from_config(config: RunConfig) -> RunForm:
    """The form values that reproduce `config`, e.g. to fill the form with the example."""
    return RunForm(
        stored_energy_mwh=config.battery_state.stored_energy_mwh,
        cycles_used=config.battery_state.cycles_used,
        commissioned_at=config.battery_state.commissioned_at,
        start=config.horizon.start,
        end=config.horizon.end,
        window_size=config.window_size,
        enforce_cycle_pace=config.options.enforce_cycle_pace,
        time_limit_seconds=config.options.time_limit_seconds,
        mip_gap=config.options.mip_gap,
        markets=tuple(
            MarketChoice(
                sheet=sheet.sheet,
                price_column=sheet.buy_price_column,
                step_length=sheet.step_length,
            )
            for sheet in config.market_sheets
        ),
    )
