import argparse
from bs4 import BeautifulSoup
import deathbycaptcha
import json
import requests
import os
import pdb
from pprint import pprint
import sys


address_dict = {}


def fetch_offender_responses(offender_ids):
    # Remove Offender IDs that are already in the address_dict
    already_found_ids = list(address_dict.keys())

    ids_to_find = list(set(offender_ids) - set(already_found_ids))
    num_found = len(address_dict)
    num_to_find = len(ids_to_find)
    expected_time = num_to_find * 0.5
    print(f"{num_found} found. {num_to_find} to find.  ETA: {expected_time} minutes")

    base_url = "https://www.criminaljustice.ny.gov/SomsSUBDirectory/ReCaptchaServlet"
    captcha_url = f"{base_url}?offenderId={offender_ids[0]}&Submit=Search"
    g_captcha_response = get_g_captcha_response(captcha_url)

    session = requests.Session()

    try:
        for offender_id in ids_to_find:
            params = {
                "offenderId": offender_id,
                "g-recaptcha-response": g_captcha_response,
                "Submit": "Search"
            }
            resp = session.get(base_url, params=params)
            soup = BeautifulSoup(resp.text, "html.parser")
            address_tags = soup.find_all("ul", {"class": "address label-value"})
            if len(address_tags) > 0:
                addresses = []
                for tag in address_tags:
                    one_address_dict = {}
                    address_type = tag.find(
                        "span", {"class": "value"}).text.replace("\xa0", " ")
                    address = tag.text.split(
                        "Address")[-1].split("View")[0].replace("\xa0", " ")
                    one_address_dict["address_type"] = address_type
                    one_address_dict["address"] = address
                    addresses.append(one_address_dict)
                address_dict[offender_id] = addresses
            else:
                fetch_offender_responses(offender_ids)
    except Exception as e:
        print(e)
        fetch_offender_responses(offender_ids[1:])


def parse_offender_urls(soup):
    offender_tag_list = soup.find_all("a", {"rel": "nofollow"})
    offender_urls = []
    for offender_tag in offender_tag_list:
        base_url = "https://www.criminaljustice.ny.gov"
        offender_rel_url = offender_tag["href"]
        offender_url = f"{base_url}{offender_rel_url}"
        offender_urls.append(offender_url)
    return offender_urls


def parse_offender_ids_from_urls(url_list):
    offender_ids = []
    for url in url_list:
        split_1 = url.split("?")[-1]
        split_2 = split_1.split("=")[1]
        split_3 = split_2.split("&")[0]
        offender_id = split_3
        offender_ids.append(offender_id)

    return offender_ids


def get_g_captcha_response(url, retries=3):
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    data_sitekey = soup.find("div", {"class": "g-recaptcha"})["data-sitekey"]

    username = os.environ.get("DBC_USERNAME", "PUT_YOUR_USERNAME_HERE")
    password = os.environ.get("DBC_PASSWORD", "PUT_YOUR_PASSWORD_HERE")

    # Put the proxy and reCaptcha token data

    Captcha_dict = {
        "googlekey": data_sitekey,
        "pageurl": url,
    }

    # Create a json string
    json_Captcha = json.dumps(Captcha_dict)

    print("Retrieving CAPTCHA - normally takes about 30 seconds")
    client = deathbycaptcha.SocketClient(username, password)
    # to use http client client = deathbycaptcha.HttpClient(username, password)
    # client = deathbycaptcha.HttpClient(username, password)

    try:
        balance = client.get_balance()
        print(f"CAPTCHA credit balance: {balance}")

        # Put your CAPTCHA type and Json payload here:
        captcha = client.decode(type=4, token_params=json_Captcha)
        if captcha:
            # The CAPTCHA was solved; captcha["captcha"] item holds its
            # numeric ID, and captcha["text"] item its list of "coordinates".
            print("CAPTCHA %s solved: %s" %
                  (captcha["captcha"], captcha["text"]))
            return captcha["text"]

            if "":  # check if the CAPTCHA was incorrectly solved
                client.report(captcha["captcha"])
        elif retries > 0:
            print(f"Retrying. {retries} retries left")
            get_g_captcha_response(url, -1)
    except deathbycaptcha.AccessDeniedException:
        # Access to DBC API denied, check your credentials and/or balance
        print("error: Access to DBC API denied," +
              "check your credentials and/or balance")


def full_function():
    p = argparse.ArgumentParser()
    p.add_argument(
        "-U",
        "--url",
        default="https://www.criminaljustice.ny.gov/SomsSUBDirectory/search_index.jsp",
        help="URL with the list of offenders"
    )
    p.add_argument(
        "-Z",
        "--zipcode",
        required=True,
        help="Zipcode to search"
    )
    args = p.parse_args(sys.argv[1:])

    url = args.url

    zipcode = args.zipcode

    g_recaptcha_response = get_g_captcha_response(url)

    # Build SERP url
    base_url = "https://www.criminaljustice.ny.gov/SomsSUBDirectory/search_index.jsp"
    search_url_params = {
        "offenderSubmit": "true",
        "LastName": "",
        "County": "",
        "Zip": zipcode,
        "g-recaptcha-response": g_recaptcha_response
    }

    serp_resp = requests.get(base_url, params=search_url_params)
    serp_soup = BeautifulSoup(serp_resp.text, "html.parser")

    offender_urls = parse_offender_urls(serp_soup)

    # Dedupe with set()
    offender_urls = list(set(offender_urls))
    pprint(offender_urls)
    offender_ids = parse_offender_ids_from_urls(offender_urls)
    pprint(offender_ids)

    print(serp_resp.url)

    fetch_offender_responses(offender_ids)

    pdb.set_trace()


def offender_test():
    offender_ids = [
        "12253",
        "5977",
        "38656",
        "31657",
        "48355",
        "788",
        "49510",
        "19327",
        "15339",
        "42062",
        "10438",
        "25599",
        "13187",
        "7265",
        "46530",
        "19946",
        "29418",
        "25892",
        "43171",
        "31229",
        "48409",
        "36320",
        "46294",
        "23434",
        "14625",
        "33344",
        "32645",
        "35566",
        "13752",
        "5799",
        "43497",
        "27941",
        "32324",
        "419",
        "661",
        "43868",
        "647",
        "15184",
        "10853",
        "34522",
        "3344",
        "43459",
        "14669",
        "23991",
        "49889",
        "33784",
        "42055",
        "19027",
        "18266",
        "28591",
        "19896",
        "5651",
        "11793",
        "17613",
        "45739",
        "37074",
        "30592",
        "23016",
        "41641",
        "10132",
        "43994",
        "23964",
        "48458",
        "30706",
        "48068",
        "50772",
        "46477",
        "6954",
        "45249",
        "45468",
        "4365",
        "40807",
        "44551",
        "32841",
        "40441",
        "33879",
        "7104",
        "22930",
        "43867",
        "20150",
        "42446",
        "25235",
        "36972",
        "19217",
        "14149",
        "44614",
        "28345",
        "43631",
        "12955",
        "36509",
        "41503",
        "29131",
        "28635",
        "40351",
        "39475",
        "7824"]
    fetch_offender_responses(offender_ids)


if __name__ == "__main__":
    full_function()
