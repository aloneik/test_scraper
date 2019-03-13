from requests import Session, Request
from datetime import date
from lxml import html
from sys import argv


URL = "https://apps.penguin.bg/fly/quote3.aspx"


""" def get_flights(
    departure_city_code, arrival_city_code,
    departure_date, arrival_date=None, passengers=1
        ):
    print departure_city_code, arrival_city_code
    print departure_date, arrival_date
    payload = {
        "lang": 2,
        "departure-city": departure_city_code,
        "arrival-city": arrival_city_code,
        "reserve-type": "",
        "departure-date": departure_date,
        "adults-children": passengers,
        "search": "Search!"
    }
    with requests.Session() as session:
        session.headers.update(HEADERS)
        response = session.get(URL, params=payload)
        if not response.status_code == 200:
            print "FFFFFFUUUUUCCCCCCCKKKKK"
            return
        parsed_body = html.fromstring(response.text)
        iframe_url, = parsed_body.xpath("//iframe/@src")
        iframe_response = session.get(iframe_url, params=payload)
        if not iframe_response.status_code == 200:
            print "FFFFUUUUUUCCCCCCKKKK222222"
        print iframe_response.request.headers
        parsed_iframe = html.fromstring(iframe_response.text)
        flights_table, = parsed_iframe\
            .xpath("//table[@id=\"flywiz_tblQuotes\"]")
        print flights_table.xpath("./tr/th[@colspan=6]/text()")
 """


def scrape(
    departure_city_code, arrival_city_code,
    departure_date, return_date=None, passengers=1
        ):
    user_input = {
        "departure_city_code": departure_city_code,
        "arrival_city_code": arrival_city_code,
        "departure_date": departure_date,
        "return_date": return_date,
        "passengers": passengers
    }
    if not is_valid_input(**user_input):
        return
    session = Session()
    request = build_request(session, URL, parse_user_input(**user_input))
    result = None
    try:
        result = parse_response(session.send(request))
    # TODO concoct exception types to catch
    except Exception as e:
        print e.message
        # check_errors(...)
    return result


def build_request(session, url, payload=None):
    request = Request("GET", url, params=payload)
    return session.prepare_request(request)


# def fetch_iframe_url(response):
#     parsed_body = html.fromstring(response.text)
#     iframe_url, = parsed_body.xpath("//iframe/@src")
#     if iframe_url:
#         return iframe_url


# TODO complete implementation
def parse_response(response):
    parsed_body = html.fromstring(response.text)
    print "i"
    iframe_elements = parsed_body.xpath("//iframe/@src")
    if iframe_elements:
        iframe_url, = iframe_elements
        if iframe_url:
            print iframe_url
            return iframe_url
    print "t", parsed_body.xpath("//table[@id=\"flywiz_tblQuotes\"]")
    with open("t.html", "w") as f:
        f.write(response.text)
    flights_table, = parsed_body.xpath("//table[@id=\"flywiz_tblQuotes\"]")
    print flights_table.xpath("./tr/th[@colspan=6]/text()")
    flights = zip(
        flights_table.xpath("./tr[contains(@id,'flywiz_rinf')]"),
        flights_table.xpath("./tr[contains(@id,'flywiz_rprc')]")
    )
    flights_info = []
    flights_info.append([
        flight[0].xpath("./td/text()")[1:] + flight[1].xpath("./td/text()")
        for flight in flights
    ])
    print flights_table.xpath("./tr[contains(@id,'flywiz_irinf')]")
    return_flights = zip(
        flights_table.xpath("./tr[contains(@id,'flywiz_irinf')]"),
        flights_table.xpath("./tr[contains(@id,'flywiz_irprc')]")
    )
    print return_flights
    if return_flights:
        flights_info.append([
            flight[0].xpath("./td/text()")[1:] + flight[1].xpath("./td/text()")
            for flight in return_flights
        ])
    return flights_info


def parse_user_input(
    departure_city_code, arrival_city_code,
    departure_date, arrival_date=None, passengers=1
        ):
    payload = {
        "ow": "",
        "lang": "en",
        "depdate": departure_date,
        "aptcode1": departure_city_code,
        "aptcode2": arrival_city_code,
        "paxcount": passengers,
        "infcount": ""
    }
    if arrival_date:
        payload["arrdate"] = arrival_date
    return payload


def is_valid_input(
    departure_city_code, arrival_city_code,
    departure_date, arrival_date=None, passengers=1
        ):
    result = True
    if len(argv) < 4:
        print """You entered <3 parameters.
            Please input departure IATA code, arrival IATA code
            and departure date."""
        result = False
    else:
        dep_date = date(
            int(departure_date.split(".")[2]),
            int(departure_date.split(".")[1]),
            int(departure_date.split(".")[0])
        )
        if date.today() > dep_date:
            print "Departure date must be >= today"
            result = False
        if arrival_date:
            arr_date = date(
                int(arrival_date.split(".")[2]),
                int(arrival_date.split(".")[1]),
                int(arrival_date.split(".")[0])
            )
            if arr_date < dep_date:
                print "Return date must be >= departure date"
                result = False
        if passengers > 8:
            print "Limit of passengers: 8"
            result = False
    return result


scrape(*argv[1:])
