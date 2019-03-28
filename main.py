import datetime as dt
from requests import get, ConnectionError
from lxml import html
from sys import argv
from itertools import product
from re import compile


URL = "https://apps.penguin.bg/fly/quote3.aspx"
IATA_CODE_RE = compile(r"^[A-Z]{3}$")


class NoSuitableFlightsError(Exception):
    def __init__(self):
        Exception.__init__(self, "No suitable flights found")


class NoDataError(Exception):
    def __init__(self):
        Exception.__init__(self, "No data from server")


class NoOugoingFlightsError(Exception):
    def __init__(self):
        Exception.__init__(self, "No outgoing flights found")


class NoReturnFlightsError(Exception):
    def __init__(self):
        Exception.__init__(self, "No return flights found")


def scrape(user_input=None):
    """Scrape flights from https://apps.penguin.bg/fly/quote3.aspx.

        If user_input = None - parse parameters from argv.
    """
    if not user_input:
        user_input = parse_input()
    incorrect_params = validate_input(user_input)
    while len(incorrect_params) > 0:
        user_input.update(reenter_user_parameters(incorrect_params))
        incorrect_params = validate_input(user_input)
    try:
        response = get(URL, params=build_request_payload(user_input))
        out, ret = parse_response(response)
        result = process_flights(out, ret, user_input)
    except ConnectionError:
        print "Server is not available. Check your network connection"
    except AssertionError:
        print "Outgoing and return flights prices are in different currencies"
    except Exception as ex:
        print str(ex)
    else:
        print_result(result)


def build_request_payload(user_input):
    payload = {
        "ow": "",
        "lang": "en",
        "depdate": user_input["departure_date"].strftime("%d.%m.%Y"),
        "aptcode1": user_input["departure_airport_code"],
        "aptcode2": user_input["arrival_airport_code"],
        "paxcount": 1,
        "infcount": ""
    }
    if user_input["arrival_date"]:
        payload["rtdate"] = user_input["arrival_date"].strftime("%d.%m.%Y")
        del payload["ow"]
        payload["rt"] = ""
    return payload


def parse_response(response):
    """Parse response:

        HTML page -> outgoing and return flights.

        Return flights as tuples of HTML elements
        with parts of flight info.
    """
    parsed_body = html.fromstring(response.text)
    flights_info = parsed_body.xpath(
        "/html/body/form[@id='form1']/div/table[@id='flywiz']/"
        "tr/td/table[@id='flywiz_tblQuotes']"
    )
    if not flights_info:
        raise NoDataError()
    flights_info = flights_info[0]
    outgoing_data = zip(
        flights_info.xpath("./tr[contains(@id,'flywiz_rinf')]"),
        flights_info.xpath("./tr[contains(@id,'flywiz_rprc')]")
    )
    if not outgoing_data:
        raise NoOugoingFlightsError()
    outgoing_flights = map(parse_flight, outgoing_data)
    return_data = zip(
        flights_info.xpath("./tr[contains(@id,'flywiz_irinf')]"),
        flights_info.xpath("./tr[contains(@id,'flywiz_irprc')]")
    )
    return_flights = None if not return_data else map(
        parse_flight, return_data)
    return outgoing_flights, return_flights


def parse_flight(flight):
    """Parse flight:

        Tuple of HTML elements -> dict with flight info.
    """
    (
        (_, flight_date, dep_time, arr_time, dep_code, arr_code),
        (_, price, bag_info)
    ) = flight
    _, amount, currency = price.xpath("./text()")[0].split()
    amount = float(amount)
    flight_date = flight_date.xpath("./text()")[0]
    dep_time = dt.datetime.strptime(
        flight_date + dep_time.xpath("./text()")[0], "%a, %d %b %y%H:%M")
    arr_time = dt.datetime.strptime(
        flight_date + arr_time.xpath("./text()")[0], "%a, %d %b %y%H:%M")
    if arr_time < dep_time:
        arr_time += dt.timedelta(days=1)
    bag_info = bag_info.xpath("./text()")
    bag_info = bag_info[0] if len(bag_info) > 0 else ""
    return {
        "dep_time": dep_time,
        "arr_time": arr_time,
        "arr_code": arr_code.xpath("./text()")[0].split()[1].strip("()"),
        "dep_code": dep_code.xpath("./text()")[0].split()[1].strip("()"),
        "price": amount,
        "currency": currency,
        "bag_info": bag_info
    }


def reenter_user_parameters(incorrect_params):
    """Request new value for every parameter in incorect_params."""
    updated_parameters = {}
    for param, error_msg in incorrect_params.items():
        print error_msg
        inp = raw_input("Enter new value: ")
        updated_parameters[param] = inp
    return updated_parameters


def process_flights(outgoing_flights, return_flights, user_input):
    """Match flights with user input.

        Combine if there is a return flights.

        Sort by price.

        Return flights options.
    """
    outgoing_flights = [
        flight for flight in outgoing_flights
        if all([
            flight["dep_code"] == user_input["departure_airport_code"],
            flight["arr_code"] == user_input["arrival_airport_code"],
            flight["dep_time"].date() == user_input["departure_date"]
        ])
    ]
    if not outgoing_flights:
        if user_input["arrival_date"]:
            pass
        else:
            raise NoSuitableFlightsError()

    if not user_input["arrival_date"]:
        return sorted(outgoing_flights, key=lambda f: f["price"])

    if not return_flights:
        raise NoReturnFlightsError()
    return_flights = [
        flight for flight in return_flights
        if all([
            flight["dep_code"] == user_input["arrival_airport_code"],
            flight["arr_code"] == user_input["departure_airport_code"],
            flight["dep_time"].date() == user_input["arrival_date"]
        ])
    ]
    if not return_flights:
        raise NoSuitableFlightsError()
    flight_options = []
    for o_flight, r_flight in product(outgoing_flights, return_flights):
        assert o_flight["currency"] == r_flight["currency"]
        flight_options.append({
            "flights": (o_flight, r_flight),
            "price": o_flight["price"] + r_flight["price"],
            "currency": o_flight["currency"]
        })

    return sorted(flight_options, key=lambda f: f["price"])


def _try_convert_date(date):
    if isinstance(date, dt.date):
        return date
    conversion_res = None
    try:
        conversion_res = dt.datetime.strptime(date, "%d.%m.%Y").date()
    except ValueError:
        pass
    return conversion_res


def _check_date_constraints(date, key, user_input):
    incorrects = {}

    min_search_date = dt.datetime.today().date()
    max_search_date = min_search_date + dt.timedelta(days=365)

    date_format_msg = "{} format must be dd.mm.yyyy"
    date_constraint_msg = "{} mustn't be in past and should not be more "\
        "than a year in future."

    date_type = key.capitalize().replace("_", " ")
    if not date:
        incorrects[key] = date_format_msg.format(date_type)
    elif date < min_search_date or date > max_search_date:
        incorrects[key] = date_constraint_msg.format(date_type)

    return incorrects


def validate_input(user_input):
    """Validate user's input.

        Return dict with incorrect parameters.
    """
    incorrect_params = {}

    for key in ("departure_airport_code", "arrival_airport_code"):
        if not IATA_CODE_RE.match(user_input[key]):
            incorrect_params[key] = "{} must be 3 "\
                "capital letters code.".format(
                    key.capitalize().replace("_", " ")
                    )

    for key in ("departure_date", "arrival_date"):
        if user_input[key] is None:
            break
        date = _try_convert_date(user_input[key])
        incorrect_date = _check_date_constraints(date, key, user_input)
        if incorrect_date:
            incorrect_params.update(incorrect_date)
            break
        elif date:
            user_input[key] = date
    else:
        if user_input["arrival_date"] < user_input["departure_date"]:
            incorrect_params["arrival_date"] = "Arrival date must be "\
                "after departure date"

    return incorrect_params


def parse_input():
    """Parse input from argv"""
    arguments = argv[1:5]
    args_count = len(arguments)
    if args_count < 3:
        print "You entered <3 parameters. Please input departure IATA code, "\
            "arrival IATA code and departure date."
        exit()
    return {
        "departure_airport_code": arguments[0],
        "arrival_airport_code": arguments[1],
        "departure_date": arguments[2],
        "arrival_date": arguments[3] if args_count > 3 else None
    }


def print_result(result):
    for option in result:
        if "flights" in option:
            print "Return flight: "
            for flight in option["flights"]:
                print "    From {dep_code} to {arr_code} departure at "\
                    "{dep_time} arrival at {arr_time}".format(**flight)
            print "Price: {price} {currency}".format(**option)
        else:
            print "From {dep_code} to {arr_code} departure at {dep_time} "\
                "arrival at {arr_time} price {price} {currency}".format(
                    **option
                )


if __name__ == "__main__":
    print scrape()
