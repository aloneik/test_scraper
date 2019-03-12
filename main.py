from requests import Session, Request
from datetime import date
from lxml import html
from sys import argv


URL = "http://www.flybulgarien.dk/en/search"
MAX_PASSENGERS = 8


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


def scrape():
    if not is_valid_input(*argv[1:]):
        return
    session = Session()
    request = build_request(session, URL, user_input=argv[1:])
    result = None
    try:
        second_request = build_request(
            session,
            parse_response(session.send(request))
        )
        result = parse_response(session.send(second_request))
    # TODO concoct exception types to catch
    except Exception as e:
        print e
        # check_errors(...)
        check_errors()
        pass
    return result


def check_errors():
    pass


def build_request(session, url, payload=None, user_input=None):
    if user_input:
        user_input = parse_user_input(*user_input)
        if payload:
            payload.update(user_input)
        else:
            payload = user_input
    request = Request("GET", url, params=payload)
    return session.prepare_request(request)


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
        "lang": 2,
        "departure-city": departure_city_code,
        "arrival-city": arrival_city_code,
        "reserve-type": "",
        "departure-date": departure_date,
        "adults-children": passengers,
        "search": "Search!"
    }
    if arrival_date:
        payload["arrival-date"] = arrival_date
    return payload


def is_valid_input(
    departure_city_code, arrival_city_code,
    departure_date, arrival_date=None, passengers=1
        ):
    if len(argv) < 4:
        print """You entered <3 parameters.
                Please input departure IATA code, arrival IATA code
                and departure date."""
        return False
    else:
        dep_date = date(
            int(departure_date.split(".")[2]),
            int(departure_date.split(".")[1]),
            int(departure_date.split(".")[0])
        )
        if date.today() > dep_date:
            print "Departure date must be >= today"
            return False
        if arrival_date:
            ret_date = date(
                int(arrival_date.split(".")[2]),
                int(arrival_date.split(".")[1]),
                int(arrival_date.split(".")[0])
            )
            print ret_date
            if ret_date < dep_date:
                print "Return date must be >= departure date"
                return False
        if passengers > MAX_PASSENGERS:
            print "Limit of passengers: 8"
            return False
    return True


print scrape()
