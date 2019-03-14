from requests import Session, Request, ConnectionError
from datetime import datetime, timedelta
from lxml import html
from sys import argv
from itertools import product
from re import compile


URL = "https://apps.penguin.bg/fly/quote3.aspx"
IATA_CODE_RE = compile(r"^[A-Z]{3}$")
DATE_FORMAT_RE = compile(r"\d{2}\.\d{2}\.\d{4}")


def scrape(
    departure_airport_code, arrival_airport_code,
    departure_date, arrival_date=None, passengers=1
):
    user_input = {
        "departure_airport_code": departure_airport_code,
        "arrival_airport_code": arrival_airport_code,
        "departure_date": departure_date,
        "arrival_date": arrival_date,
        "passengers": passengers
    }
    is_valid, incorrect_params = is_valid_input(**user_input)
    if not is_valid:
        user_input.update(reenter_user_parameters(incorrect_params))
    session = Session()
    request = build_request(session, URL, user_input)
    out, ret, response = None, None, None
    is_request_succesfull = True
    try:
        response = session.send(request)
        out, ret = parse_response(response)
    except Exception as e:
        is_request_succesfull = False
        print e.message
        check_errors(e, response)
    result = None
    if is_request_succesfull:
        result = process_flights(out, ret, user_input)
    return result


def check_errors(exception, responce):
    if isinstance(exception, ConnectionError):
        print "Server is not available. Check your network connection"
    if isinstance(exception, IndexError):
        print "No data parsed"


def build_request(session, url, user_input):
    payload = {
        "ow": "",
        "lang": "en",
        "depdate": user_input["departure_date"],
        "aptcode1": user_input["departure_airport_code"],
        "aptcode2": user_input["arrival_airport_code"],
        "paxcount": user_input["passengers"],
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
    return_flights = None if return_data is None else map(
        parse_flight, return_data)
    return outgoing_flights, return_flights


def parse_flight(flight):
    (
        (cb, date, dep_time, arr_time, dep_code, arr_code),
        (_, price, bag_info)
    ) = flight
    amount, currency = price.xpath("./text()")[0].split()[1:]
    amount = float(amount)
    date = date.xpath("./text()")[0]  # "%a, %d %b %y"
    dep_time = datetime.strptime(
        date + dep_time.xpath("./text()")[0], "%a, %d %b %y%H:%M")
    arr_time = datetime.strptime(
        date + arr_time.xpath("./text()")[0], "%a, %d %b %y%H:%M")
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
    for param in incorrect_params:
        print param["error_msg"]
        answer = raw_input("Do You want to enter other value?(y/n) ")
        if answer == "y":
            updated_parameters[param["param"]] = raw_input("Enter new value: ")
    return updated_parameters


def process_flights(outgoing_flights, return_flights, user_input):
    outgoing_flights = filter(lambda f: all([
        f["dep_code"] == user_input["departure_airport_code"],
        f["arr_code"] == user_input["arrival_airport_code"],
        f["dep_time"].date() == datetime.strptime(
            user_input["departure_date"], "%d.%m.%Y"
        ).date()
    ]), outgoing_flights)
    if user_input["arrival_date"] is None:
        return sorted(outgoing_flights, key=lambda f: f["price"])
    return_flights = filter(lambda f: all([
        f["dep_code"] == user_input["arrival_airport_code"],
        f["arr_code"] == user_input["departure_airport_code"],
        f["dep_time"].date() == datetime.strptime(
            user_input["arrival_date"], "%d.%m.%Y"
        ).date()
    ]), return_flights)
    flight_options = []
    for o_flight, r_flight in product(outgoing_flights, return_flights):
        assert o_flight["currency"] == r_flight["currency"]
        flight_options.append({
            "flights": (o_flight, r_flight),
            "price": o_flight["price"] + r_flight["price"],
            "currency": o_flight["currency"]
        })
    return sorted(flight_options, key=lambda f: f["price"])


def validate_airport_codes(departure_airport_code, arrival_airport_code):
    incorrect_params = []
    if not IATA_CODE_RE.match(departure_airport_code):
        incorrect_params.append({
            "param": "departure_airport_code",
            "error_msg": "Invalid departure code. "
            "It must be 3 capital letters code"
        })
    if not IATA_CODE_RE.match(arrival_airport_code):
        incorrect_params.append({
            "param": "arrival_airport_code",
            "error_msg": "Invalid arrival code. "
            "It must be 3 capital letters code"
        })
    return incorrect_params


def validate_departure_date(departure_date):
    incorrect_params = []
    if not DATE_FORMAT_RE.match(departure_date):
        incorrect_params.append({
            "param": "departure_date",
            "error_msg": "Invalid departure date format. "
            "it must be dd.mm.yyyy"
        })
    else:
        dep_date = datetime.strptime(departure_date, "%d.%m.%Y")
        if dep_date < datetime.today():
            incorrect_params.append({
                "param": "departure_date",
                "error_msg": "Departure date({}) must not be in past".format(
                    dep_date.strftime("%d.%m.%Y")
                )
            })
    return incorrect_params


def validate_arrival_date(departure_date, arrival_date):
    incorrect_params = []
    if not DATE_FORMAT_RE.match(arrival_date):
        incorrect_params.append({
            "param": "arrival_date",
            "error_msg": "Invalid arrival date format. "
            "it must be dd.mm.yyyy"
        })
    elif arrival_date:
        dep_date = datetime.strptime(departure_date, "%d.%m.%Y")
        arr_date = datetime.strptime(arrival_date, "%d.%m.%Y")
        if arr_date < dep_date:
            incorrect_params.append({
                "param": "arrival_date",
                "error_msg": "Return date({}) must be after "
                "departure date({})".format(
                    arr_date.strftime("%d.%m.%Y"),
                    dep_date.strftime("%d.%m.%Y")
                )
            })
    return incorrect_params


def is_valid_input(
    departure_airport_code, arrival_airport_code,
    departure_date, arrival_date, passengers
):
    result = True
    incorrect_params = []
    # TODO: refactor dates and codes validation
    incorrect_params.extend(
        validate_airport_codes(departure_airport_code, arrival_airport_code)
    )
    departure_date_errors = validate_departure_date(departure_date)
    incorrect_params.extend(departure_date_errors)
    if len(departure_date_errors) == 0:
        incorrect_params.extend(
            validate_arrival_date(departure_date, arrival_date)
        )
    passengers = int(passengers)
    if 1 > passengers > 8:
        incorrect_params.append({
            "param": "passengers",
            "error_msg": "Passengers count must be from 1 to 8. "
            "You entered {}".format(passengers)
        })
    if len(incorrect_params) > 0:
        result = False
    return result, incorrect_params


if len(argv) < 4:
    print """You entered <3 parameters.
Please input departure IATA code, arrival IATA code and departure date."""
    exit()
result = scrape(*argv[1:])
if result is None or len(result) == 0:
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
