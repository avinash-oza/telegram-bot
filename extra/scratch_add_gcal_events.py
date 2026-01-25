import argparse
import logging
from datetime import datetime, timedelta

import pandas as pd
from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s"
)

logger = logging.getLogger(__name__)


def read_events_file(file_path):
    logger.info(f"Reading events from file_path={file_path}")
    events_df = pd.read_csv(file_path)
    events_df["event_date_start"] = pd.to_datetime(
        events_df["event_date_start"], format="%m/%d/%Y"
    ).dt.tz_localize(None)
    events_df["event_date_end"] = pd.to_datetime(
        events_df["event_date_end"], format="%m/%d/%Y"
    ).dt.tz_localize(None)

    logger.info(f"Read {len(events_df)} events from file_path={file_path}")

    return events_df


def add_events(events_df, calendar, dry_run):
    s = events_df["event_date_start"].min()
    e = events_df["event_date_start"].max() + timedelta(hours=1)

    existing_events = set()

    for e in calendar.get_events(time_min=s, time_max=e):
        event_key = (
            e.summary,
            e.start.replace(tzinfo=None) if isinstance(e.start, datetime) else e.start,
            e.end.replace(tzinfo=None) if isinstance(e.end, datetime) else e.end,
        )
        existing_events.add(event_key)

    for idx, row in events_df.iterrows():
        event_name = row["event_name"]
        event_start_time = row["event_date_start"].to_pydatetime()
        event_end_time = row["event_date_end"].to_pydatetime()
        location = row["location"]
        is_all_day = row["all_day"]
        if is_all_day:
            event_start_time = event_start_time.date()
            # Legacy existing events have the event ending one day later
            event_end_time = event_end_time.date() + timedelta(days=1)

        event_key = (event_name, event_start_time, event_end_time)
        if event_key in existing_events:
            logger.info(
                f"Skipping event_name={event_name} with start={event_start_time},end={event_end_time},location={location} as it exists"
            )
            continue

        logger.info(
            f"Adding event_name={event_name} with start={event_start_time},end={event_end_time},location={location}"
        )

        if not dry_run:
            e = Event(
                event_name,
                start=event_start_time,
                end=event_end_time,
                location=location,
                default_reminders=True,
            )
            calendar.add_event(e)


def main():
    parser = argparse.ArgumentParser(description="Adds events from a file to calendar")
    parser.add_argument("--calendar-id", type=str, help="Google calendar id")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print out what is being done but don't do it",
    )
    parser.add_argument(
        "--events-file-path",
        type=str,
        required=True,
        help="CSV file containing events to be added",
    )

    args = parser.parse_args()
    calendar_id = args.calendar_id
    dry_run = args.dry_run
    events_file_path = args.events_file_path

    logger.info(f"Calendar id={calendar_id}")
    if dry_run:
        logger.info(f"Dry run mode enabled, no changes will be made")

    cal = GoogleCalendar(calendar_id)

    df_events = read_events_file(events_file_path)

    # TODO: DELETE THIS CODE FOR DELETING
    # if not dry_run:
    #     logger.info(f"Wiping calendar before adding new events to it")
    #     s = df_events["event_date_start"].min()
    #     e = df_events["event_date_start"].max() + timedelta(hours=1)
    #     for e in cal.get_events(time_min=s, time_max=e):
    #         logger.info(f"Deleting event={e.summary}")
    #         cal.delete_event(e)

    future_events_df = df_events[
        df_events["event_date_start"] >= pd.Timestamp.now(tz=None)
    ]
    if future_events_df.empty:
        logger.warning(f"No events in the future to add")
        return

    add_events(df_events, cal, dry_run)


if __name__ == "__main__":
    main()
