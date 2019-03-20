from requests import Session, Request, ConnectionError
from datetime import datetime, timedelta, date
from lxml import html
from sys import argv
from itertools import product
from re import compile


URL = "https://apps.penguin.bg/fly/quote3.aspx"
IATA_CODE_RE = compile(r"^[A-Z]{3}$")
DATE_FORMAT_RE = compile(r"^\d{2}\.\d{2}\.\d{4}$")


class NoAvailableFlightsError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def scrape(
    departure_airport_code, arrival_airport_code,
    departure_date, arrival_date=None
        ):
    user_input = {
        "departure_airport_code": departure_airport_code,
        "arrival_airport_code": arrival_airport_code,
        "departure_date": departure_date,
        "arrival_date": arrival_date
    }
    incorrect_params = is_valid_input(**user_input)
    while len(incorrect_params) > 0:
        user_input.update(reenter_user_parameters(incorrect_params))
        incorrect_params = is_valid_input(**user_input)
    session = Session()
    request = build_request(session, URL, user_input)
    out, ret, response = None, None, None
    result = None
    try:
        response = session.send(request)
        out, ret = parse_response(response)
        result = process_flights(out, ret, user_input)
    except Exception as e:
        check_errors(e, response)
    return result


def check_errors(exception, response):
    if isinstance(exception, ConnectionError):
        print "Server is not available. Check your network connection"
    elif response.status_code != 200:
        print "Bad response"
    elif isinstance(exception, IndexError):
        if "internal error occurred" in response.text:
            print "An internal error occurred. Please retry your request."
    elif isinstance(exception, NoAvailableFlightsError):
        print "No available flights"
    elif isinstance(exception, AssertionError):
        print "Outgoing and return flights prices are in different "\
            "currencies"


def build_request(session, url, user_input):
    payload = {
        "ow": "",
        "lang": "en",
        "depdate": user_input["departure_date"],
        "aptcode1": user_input["departure_airport_code"],
        "aptcode2": user_input["arrival_airport_code"],
        "paxcount": 1,
        "infcount": ""
    }
    if user_input["arrival_date"] is not None:
        payload["rtdate"] = user_input["arrival_date"]
        del payload["ow"]
        payload["rt"] = ""
    request = Request("GET", url, params=payload)
    return session.prepare_request(request)


def parse_response(response):
    parsed_body = html.fromstring(response.text)
    flights_info = parsed_body.xpath(
        "/html/body/form[@id='form1']/div/table[@id='flywiz']/"
        "tr/td/table[@id='flywiz_tblQuotes']"
    )[0]
    outgoing_data = zip(
        flights_info.xpath("./tr[contains(@id,'flywiz_rinf')]"),
        flights_info.xpath("./tr[contains(@id,'flywiz_rprc')]")
    )
    outgoing_flights = map(parse_flight, outgoing_data)
    return_data = zip(
        flights_info.xpath("./tr[contains(@id,'flywiz_irinf')]"),
        flights_info.xpath("./tr[contains(@id,'flywiz_irprc')]")
    )
    return_flights = None if not return_data else map(
        parse_flight, return_data)
    return outgoing_flights, return_flights


def parse_flight(flight):
    (
        (_, flight_date, dep_time, arr_time, dep_code, arr_code),
        (_, price, bag_info)
    ) = flight
    _, amount, currency = price.xpath("./text()")[0].split()
    amount = float(amount)
    flight_date = flight_date.xpath("./text()")[0]
    dep_time = datetime.strptime(
        flight_date + dep_time.xpath("./text()")[0], "%a, %d %b %y%H:%M")
    arr_time = datetime.strptime(
        flight_date + arr_time.xpath("./text()")[0], "%a, %d %b %y%H:%M")
    if arr_time < dep_time:
        arr_time += timedelta(days=1)
    return {
        "dep_time": dep_time,
        "arr_time": arr_time,
        "arr_code": arr_code.xpath("./text()")[0].split()[1].strip("()"),
        "dep_code": dep_code.xpath("./text()")[0].split()[1].strip("()"),
        "price": amount,
        "currency": currency,
        "bag_info": bag_info.xpath("./text()")[0]
    }


def reenter_user_parameters(incorrect_params):
    updated_parameters = {}
    for param, error_msg in incorrect_params.items():
        print error_msg
        inp = raw_input("Enter new value: ")
        updated_parameters[param] = inp
    return updated_parameters


def process_flights(outgoing_flights, return_flights, user_input):
    if outgoing_flights is None:
        raise NoAvailableFlightsError()
    outgoing_flights = [
        flight for flight in outgoing_flights
        if all([
            flight["dep_code"] == user_input["departure_airport_code"],
            flight["arr_code"] == user_input["arrival_airport_code"],
            flight["dep_time"].date() == datetime.strptime(
                user_input["departure_date"], "%d.%m.%Y"
            ).date()
        ])
    ]
    if user_input["arrival_date"] is None:
        return sorted(outgoing_flights, key=lambda f: f["price"])
    if return_flights is None:
        raise NoAvailableFlightsError()
    return_flights = [
        flight for flight in return_flights
        if all([
            flight["dep_code"] == user_input["arrival_airport_code"],
            flight["arr_code"] == user_input["departure_airport_code"],
            flight["dep_time"].date() == datetime.strptime(
                user_input["arrival_date"], "%d.%m.%Y"
            ).date()
        ])
    ]
    flight_options = []
    for o_flight, r_flight in product(outgoing_flights, return_flights):
        assert o_flight["currency"] == r_flight["currency"]
        flight_options.append({
            "flights": (o_flight, r_flight),
            "price": o_flight["price"] + r_flight["price"],
            "currency": o_flight["currency"]
        })
    return sorted(flight_options, key=lambda f: f["price"])


def is_date_less(first_date, second_date, format="%d.%m.%Y"):
    if not isinstance(first_date, date):
        first_date = datetime.strptime(first_date, format).date()
    if not isinstance(second_date, date):
        second_date = datetime.strptime(second_date, format).date()
    return first_date < second_date


def is_valid_input(
    departure_airport_code, arrival_airport_code,
    departure_date, arrival_date
        ):
    incorrect_params = {}
    if not IATA_CODE_RE.match(departure_airport_code):
        incorrect_params["departure_airport_code"] = "Invalid departure code."\
            " It must be 3 capital letters code."
    if not IATA_CODE_RE.match(arrival_airport_code):
        incorrect_params["arrival_airport_code"] = "Invalid arrival code."\
            " It must be 3 capital letters code."
    if not DATE_FORMAT_RE.match(departure_date):
        incorrect_params["departure_date"] = "Departure date format must "\
            "be dd.mm.yyyy"
    elif not is_date_less(datetime.today().date(), departure_date):
        incorrect_params["departure_date"] = "Departure date mustn't "\
            "be in past"
    elif arrival_date is not None:
        if not DATE_FORMAT_RE.match(arrival_date):
            incorrect_params["arrival_date"] = "Arrival date format must "\
                "be dd.mm.yyyy"
        elif not is_date_less(departure_date, arrival_date):
            incorrect_params["arrival_date"] = "Arrival date must be after "\
                "departure date"
    return incorrect_params


if len(argv) < 4:
    print """You entered <3 parameters.
Please input departure IATA code, arrival IATA code and departure date."""
    exit()
result = scrape(*argv[1:5])
if not result:
    print "Flights on your request not found"
    exit()
for option in result:
    if "flights" in option:
        print "Return flight: "
        for flight in option["flights"]:
            print "    From {dep_code} to {arr_code} departure at {dep_time} "\
                "arrival at {arr_time}".format(**flight)
        print "Price: {price} {currency}".format(**option)
    else:
        print "From {dep_code} to {arr_code} departure at {dep_time} arrival "\
            "at {arr_time} price {price} {currency}".format(**option)
