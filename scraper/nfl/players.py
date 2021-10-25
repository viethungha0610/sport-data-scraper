from typing import List, Dict, Union
import pandas as pd
import requests
import re
import string
from bs4 import BeautifulSoup
from bs4.element import Tag
from datetime import datetime
import time


# Script configuration vars
BASE_SITE_URL = "https://www.pro-football-reference.com"
BASE_PLAYERS_URL = "https://www.pro-football-reference.com/players"
HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
    )
}
ALPHABETS_LIST = [letter for letter in string.ascii_uppercase]
TODAY_STR = datetime.today().strftime("%Y%m%d")


def gather_player_links(
    base_player_url: str = BASE_PLAYERS_URL,
    headers: dict = HEADERS,
    letter: str = None,
    start_threshold: int = 2016,
) -> List[str]:
    """
    Function to scrape the links to the profiles of players whose last name starts with a letter (input)
    Args:
        base_url (str): base_url to attach index letter to
        headers (dict): GET requests headers
        letter (str): index letter, signififying the starting letter of players' last name
        start_threshold (int): integer specifying the year the player start their career in the NFL. This is to limit the number of requests and get more relevant data.
    Returns:
        player_links_list (List[str])
    """
    letter_url = f"{base_player_url}/{letter}/"
    letter_response = requests.get(letter_url, headers=headers)
    letter_soup = BeautifulSoup(letter_response.content, "html.parser")
    player_links_list = []
    for tag in letter_soup.find_all(
        "a", {"href": re.compile(f"(\/players\/{letter}\/)(.*)(\.htm)")}
    ):
        try:
            # If the parent tag is <b> i.e. bold -> signifies current player
            if tag.parent.name == "b":
                # Specifying the year the player starts in the NFL
                if (
                    int(tag.parent.parent.text.split()[-1].split("-")[0])
                    >= start_threshold
                ):
                    player_links_list.append(tag["href"])
        except AttributeError:
            continue
    return player_links_list


def ft_in_to_cm(ft_in: str, delimiter: str = "-") -> int:
    """
    Function to convert feet and inches measurement to cm
    """
    ft_in_split_str = ft_in.split(delimiter)
    fts = ft_in_split_str[0]
    inches = ft_in_split_str[1]
    cm_output = int(fts) * 30.48 + int(inches) * 2.48
    return int(cm_output)


def get_player_soup(
    base_site_url: str = BASE_SITE_URL, player_link: str = None, headers: dict = HEADERS
) -> BeautifulSoup:
    """
    Function to get a BeautifulSoup HTML Content of a player info, to be used as an input for a downstream function
    Args:
        base_url (str): base_url to attach index letter to
        headers (dict): GET requests headers
        player_link (str): a suffix of the player url, to be attached onto the base URL
    Return:
        player_soup (bs4.BeautifulSoup): a player's BeautifulSoup HTML content
    """
    player_url = f"{base_site_url}{player_link}"
    player_response = requests.get(player_url, headers=headers)
    player_soup = BeautifulSoup(player_response.content, "html.parser")
    return player_soup


def get_career_stat_from_datatip(element_tag: Tag, datatip: str) -> Union[str, None]:
    """
    Function to get a career stat as string from an element tag and a datatip
    Args:
        element_tag (bs4.element.Tag): a player's specific stat element HTML Tag
        datatip (str): the datatip that shows up when hovering above the stat on the website
    Returns:
        stat_str (str): the string indicating the career statistic
            or
        None: if that stat is not found on the page
    """
    try:
        stat_str = (
            element_tag.find("span", {"data-tip": datatip})
            .find_next_siblings("p")[-1]
            .contents[0]
        )
        return stat_str
    except AttributeError:  # This means the stat is not relevant for that position e.g. Sacks for QB
        return None
    except IndexError:
        return None


def gather_player_info(player_soup: BeautifulSoup) -> Dict[str, str]:
    """
    Function to intake a player's BeautifulSoup HTML content and extract player info
    Args:
        player_soup (bs4.BeautifulSoup): a player's BeautifulSoup HTML content
    Return:
        player_info (dict): a dictionary containing player's info
    """

    # Initialising an empty dictionary to store player's info
    player_info = {}

    # Profile and metadata
    player_info_tag = player_soup.find("div", {"id": "info", "class": "players"})
    player_info["name"] = (
        player_info_tag.find("h1", itemprop="name").find("span").contents[0]
    )
    player_info["team"] = (
        player_info_tag.find("span", itemprop="affiliation").find("a").contents[0]
    )
    player_info["position"] = re.match(
        r"[A-Z]",
        player_info_tag.find("strong", text="Position").next_sibling.split(": ")[1],
    )[0]
    player_info["height"] = ft_in_to_cm(
        player_info_tag.find("span", itemprop="height").contents[0]
    )
    player_info["weight"] = player_info_tag.find("span", itemprop="weight").contents[0]
    player_info["birth_date"] = player_info_tag.find("span", itemprop="birthDate")[
        "data-birth"
    ]
    player_info["awards"] = [
        award_tag.get_text()
        for award_tag in player_info_tag.find_all("a", href="/awards/")
    ]

    # Careers stats datatips - These are our only hints to get to the data
    gp_datatip = "Games played"
    av_datatip = "Approximate Value is our attempt to attach a single number to every player-season since 1960.<br>See the glossary for more information."
    qbrec_datatip = "Team record in games started by this QB (regular season)"
    cmp_pct_datatip = "Percentage of Passes Completed<br>Minimum 14 attempts per scheduled game to qualify as leader.<br />Minimum 1500 pass attempts to qualify as career leader."
    yds_pass_datatip = (
        "Yards Gained by Passing<br>For teams, sack yardage is deducted from this total"
    )
    ya_pass_datatip = "Yards gained per pass attempt <br>Minimum 14 attempts per scheduled game to qualify as leader.<br>Minimum 1500 pass attempts to qualify as career leader."
    passing_td_datatip = "Passing Touchdowns"
    int_thrown_datatip = "Interceptions thrown"
    sacks_datatip = "Sacks (official since 1982,<br />based on play-by-play, game film<br />and other research since 1960)"
    solo_datatip = "Tackles<br>Before 1994:  unofficial and inconsistently recorded from team to team.  For amusement only.<br>1994-now:  unofficial but consistently recorded.<br>"
    ff_datatip = (
        "Number of times forced a fumble by the opposition recovered by either team"
    )
    fantpt_datatip = """<b>Fantasy points:</b><br />
								1 point per 25 yards passing<br />
								4 points per passing touchdown<br />
								-2 points per interception thrown<br />
								1 point per 10 yards rushing/receiving<br />
								6 points per TD<br />
								2 points per two-point conversion<br />
								-2 points per fumble lost (est. prior to 1994)"""
    ## WR stat
    rec_datatip = "Receptions"
    yds_receive_datatip = "Receiving Yards"
    yr_datatip = "Receiving Yards per Reception<br>Minimum 1.875 catches per game scheduled to qualify as leader.<br />Minimum 200 receptions to qualify as career leader."
    receiving_td_datatip = "Receiving Touchdowns"

    ## RB stats
    rush_datatip = "Rushing Attempts (sacks not included in NFL)"
    yds_rush_datatip = "Rushing Yards Gained (sack yardage is not included by NFL)"
    ya_rush_datatip = "Rushing Yards per Attempt<br>Minimum 6.25 rushes per game scheduled to qualify as leader.<br />Minimum 750 rushes to qualify as career leader."
    rushing_td_datatip = "Rushing Touchdowns"

    ## Scraping player performance info
    player_career_stats_tag = player_soup.find("div", {"class": "stats_pullout"})
    player_info["career_stats"] = {
        "games_played": get_career_stat_from_datatip(
            player_career_stats_tag, gp_datatip
        ),
        "approx_val": get_career_stat_from_datatip(player_career_stats_tag, av_datatip),
        "qbrec": get_career_stat_from_datatip(player_career_stats_tag, qbrec_datatip),
        "cmp_pct": get_career_stat_from_datatip(
            player_career_stats_tag, cmp_pct_datatip
        ),
        "yds_pass": get_career_stat_from_datatip(
            player_career_stats_tag, yds_pass_datatip
        ),
        "ya_pass": get_career_stat_from_datatip(
            player_career_stats_tag, ya_pass_datatip
        ),
        "passing_td": get_career_stat_from_datatip(
            player_career_stats_tag, passing_td_datatip
        ),
        "int_thrown": get_career_stat_from_datatip(
            player_career_stats_tag, int_thrown_datatip
        ),
        "sacks": get_career_stat_from_datatip(player_career_stats_tag, sacks_datatip),
        "solo": get_career_stat_from_datatip(player_career_stats_tag, solo_datatip),
        "ff": get_career_stat_from_datatip(player_career_stats_tag, ff_datatip),
        "rec": get_career_stat_from_datatip(player_career_stats_tag, rec_datatip),
        "yds_receive": get_career_stat_from_datatip(
            player_career_stats_tag, yds_receive_datatip
        ),
        "yr": get_career_stat_from_datatip(player_career_stats_tag, yr_datatip),
        "receiving_td": get_career_stat_from_datatip(
            player_career_stats_tag, receiving_td_datatip
        ),
        "rush": get_career_stat_from_datatip(player_career_stats_tag, rush_datatip),
        "yds_rush": get_career_stat_from_datatip(
            player_career_stats_tag, yds_rush_datatip
        ),
        "ya_rush": get_career_stat_from_datatip(
            player_career_stats_tag, ya_rush_datatip
        ),
        "rushing_td": get_career_stat_from_datatip(
            player_career_stats_tag, rushing_td_datatip
        ),
        "fantpt": get_career_stat_from_datatip(player_career_stats_tag, fantpt_datatip),
    }

    return player_info


def scrape_nfl_player_data(start_year: int = 2016) -> pd.DataFrame:
    player_info_list = []
    for letter in ALPHABETS_LIST:
        player_links_list = gather_player_links(
            letter=letter, start_threshold=start_year
        )
        for player_link in player_links_list:
            try:
                player_soup = get_player_soup(player_link=player_link)
                player_info_dict = gather_player_info(player_soup=player_soup)
                player_info_list.append(player_info_dict)
            except AttributeError:  # This error occurs with players who no longer plays in the league
                continue
            except ConnectionResetError:  # This error can occur if the server throttles the request
                time.sleep(5)
                continue
    print(f"Collected info on {len(player_info_list)} players!")
    scraped_players_data_df = pd.json_normalize(player_info_list)
    scraped_players_data_df.drop_duplicates(
        subset=["name", "team", "position", "height", "weight", "birth_date"],
        inplace=True,
    )
    print(scraped_players_data_df.shape)
    scraped_players_data_df
