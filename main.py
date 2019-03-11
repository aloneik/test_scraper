from requests import Session, Request
from datetime import date
from lxml import html
from sys import argv


URL = "http://www.flybulgarien.dk/en/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:65.0) Gecko/"
    "20100101 Firefox/65.0"
}
MAX_PASSENGERS = 8
NOT_ENOGHT_PARAMETERS = """You entered <3 parameters.
Please input departure IATA code, arrival IATA code
and departure date."""


""" def get_flights(
    departure_city_code, arrival_city_code,
    departure_date, return_date=None, passengers=1
        ):
    print departure_city_code, arrival_city_code
    print departure_date, return_date
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
        filghts_table, = parsed_iframe\
            .xpath("//table[@id=\"flywiz_tblQuotes\"]")
        print filghts_table.xpath("./tr/th[@colspan=6]/text()")
 """


def scrape():
    if validation(*argv[1:]):
        # request(...)
        session = Session()
        request = build_request(session, URL, parse_user_input(*argv[1:]))
        try:
            request = build_request(
                session,
                fetch_iframe_url(session.send(request))
                )
            return parse_response(session.send(request))
        # TODO concoct exception types to catch
        except:
            # check_errors(...)
            pass


def build_request(session, url, payload=None):
    request = Request("GET", url, params=payload)
    return session.prepare_request(request)


def fetch_iframe_url(response):
    parsed_body = html.fromstring(response.text)
    iframe_url, = parsed_body.xpath("//iframe/@src")
    if iframe_url:
        return iframe_url


# TODO complete implementation
def parse_response(response):
    parsed_body = html.fromstring(response.text)
    filghts_table, = parsed_body.xpath("//table[@id=\"flywiz_tblQuotes\"]")
    print filghts_table.xpath("./tr/th[@colspan=6]/text()")


def parse_user_input(
    departure_city_code, arrival_city_code,
    departure_date, return_date=None, passengers=1
        ):
    payload = {
        "lang": 2,
        "departure-city": departure_city_code,
        "arrival-city": arrival_city_code,
        "reserve-type": "",
        "departure-date": departure_date,
        "adults-children": passengers,
        "search": "Search!"
    }
    return payload


def validation(
    departure_city_code, arrival_city_code,
    departure_date, return_date=None, passengers=1
        ):
    if len(argv) < 4:
        print NOT_ENOGHT_PARAMETERS
        return False
    else:
        dep_date = date(
            int(departure_date.split(".")[2]),
            int(departure_date.split(".")[1]),
            int(departure_date.split(".")[0])
        )
        # Write good check
        if date.today() > dep_date:
            print "Departure date must be >= today"
            return False
        if return_date:
            ret_date = date(
                int(return_date.split(".")[2]),
                int(return_date.split(".")[1]),
                int(return_date.split(".")[0])
            )
            print ret_date
            if ret_date < dep_date:
                print "Return date must be >= departure date"
                return False
        if passengers > MAX_PASSENGERS:
            print "Limit of passengers: 8"
            return False
    return True


validation(*argv[1:])
scrape()
