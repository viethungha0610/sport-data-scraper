import os
from typing import Iterable
import numpy as np
import pandas as pd
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup


# Config vars
INJURY_REPORT_BASE_URL = "https://www.nfl.com/injuries/league"
HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
    )
}
TODAY_STR = datetime.today().strftime("%Y%m%d")
NFL_SEASON_PERIOD_LIST = [
    "REG1",
    "REG2",
    "REG3",
    "REG4",
    "REG5",
    "REG6",
    "REG7",
    "REG8",
    "REG9",
    "REG10",
    "REG11",
    "REG12",
    "REG13",
    "REG14",
    "REG15",
    "REG16",
    "REG17",
    "POST1",
    "POST2",
    "POST3",
    "PRO1",
    "POST4",
]
NFL_SEASON_YEAR_LIST = np.arange(2000, 2022, 1)


# Custom Exception class to throw an error when NFL Season period is not available
class InjuryDataNotAvailableError(Exception):
    def __init__(
        self,
        message="Could not find any injury details here, please check if the year or the period exists (e.g. not in the future).",
    ):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


def get_injury_report_df(
    base_site_url: str = INJURY_REPORT_BASE_URL, year: int = None, period: str = None
) -> pd.DataFrame:
    assert (
        1965 <= year <= int(datetime.today().strftime("%Y"))
    ), "The year must be between 1965 and this year!"
    assert (
        period in NFL_SEASON_PERIOD_LIST
    ), "Please enter a valid NFL season period code! Refer to the Documentation."
    injury_report_url = f"{base_site_url}/{str(year)}/{str(period)}"
    injury_report_response = requests.get(injury_report_url, headers=HEADERS)
    injury_report_soup = BeautifulSoup(injury_report_response.content, "html.parser")
    injury_report_table_tags_list = injury_report_soup.find_all(
        "table", {"class": "d3-o-table d3-o-table--detailed d3-o-reports--detailed"}
    )
    if len(injury_report_table_tags_list) == 0:
        raise InjuryDataNotAvailableError
    injury_df = pd.concat(pd.read_html(str(injury_report_table_tags_list)))
    # Adding Season year and Period timeline
    injury_df["Year"] = year
    injury_df["Period"] = period
    # Only keep information about injuries
    injury_df.dropna(subset=["Injuries"], inplace=True)
    injury_df.reset_index(drop=True, inplace=True)
    return injury_df


def scrape_nfl_injury_data(
    years: Iterable[int] = NFL_SEASON_YEAR_LIST,
    periods: Iterable[str] = NFL_SEASON_PERIOD_LIST,
) -> pd.DataFrame:
    scraped_output_df_list = []
    # Looping through all the years
    for year in years:
        print(f"Scraping NFL injury data from year {year}")
        # Looping through all the regular season periods and post-season periods within each year
        for period in periods:
            try:
                temp_df = get_injury_report_df(year=year, period=period)
                scraped_output_df_list.append(temp_df)
            except InjuryDataNotAvailableError:
                continue
    scraped_output_df = pd.concat(scraped_output_df_list)
    print(f"Scraped data shape: {scraped_output_df.shape}")
    return scraped_output_df
