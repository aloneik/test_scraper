from requests import Session, Request
from datetime import datetime
from lxml import html
from sys import argv
from itertools import product


URL = "https://apps.penguin.bg/fly/quote3.aspx"


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
    is_valid, incorect_params = is_valid_input(**user_input)
    if not is_valid:
        user_input.update(reenter_user_parameters(incorect_params))
        if not is_valid_input(**user_input)[0]:
            return
    session = Session()
    request = build_request(session, URL, parse_user_input(**user_input))
    # try:
    #     result = parse_response(session.send(request))
    # # TODO find exception types to catch
    # except Exception as e:
    #     print e.message
    #     # check_errors(...)
    response = session.send(request)
    out, ret = parse_response(response)
    return process_flights(out, ret, user_input)


def check_errors(exception, responce):
    pass


def build_request(session, url, payload=None):
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
    return_flights = None
    if return_data:
        return_flights = map(parse_flight, return_data)
    return outgoing_flights, return_flights


def parse_flight(flight):
    (
        (cb, date, dep_time, arr_time, dep_code, arr_code),
        (_, price, bag_info)
    ) = flight
    amount, currency = price.xpath("./text()")[0].split()[1:]
    amount = float(amount)
    date = parse_date(date.xpath("./text()")[0])
    dep_time = datetime.strptime(dep_time.xpath("./text()")[0], "%H:%M").time()
    arr_time = datetime.strptime(arr_time.xpath("./text()")[0], "%H:%M").time()
    next_day = dep_time > arr_time
    dep_time = datetime.combine(date, dep_time)
    if next_day:
        date = datetime(date.year, date.month, date.day + 1)
    arr_time = datetime.combine(date, arr_time)
    return {
        "dep_time": dep_time,
        "arr_time": arr_time,
        "arr_code": arr_code.xpath("./text()")[0].split()[1].strip("()"),
        "dep_code": dep_code.xpath("./text()")[0].split()[1].strip("()"),
        "price": amount,
        "currency": currency,
        "bag_info": bag_info.xpath("./text()")
    }


def parse_date(date):
    day, month, year = date.split()[1:]
    if len(day) == 1:
        day = "0" + day
    return datetime.strptime("".join([day, month, year]), "%d%b%y").date()


def parse_user_input(
    departure_airport_code, arrival_airport_code,
    departure_date, arrival_date, passengers
        ):
    payload = {
        "ow": "",
        "lang": "en",
        "depdate": departure_date,
        "aptcode1": departure_airport_code,
        "aptcode2": arrival_airport_code,
        "paxcount": passengers,
        "infcount": ""
    }
    if arrival_date:
        payload["rtdate"] = arrival_date
        del payload["ow"]
        payload["rt"] = ""
    return payload


def reenter_user_parameters(incorect_params):
    updated_parameters = {}
    for param in incorect_params:
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


def is_valid_input(
    departure_airport_code, arrival_airport_code,
    departure_date, arrival_date, passengers
        ):
    result = True
    incorect_params = []
    if (
        not departure_airport_code.isalpha()
        or not departure_airport_code.isupper()
        or len(departure_airport_code) != 3
            ):
        error_msg = "Departure airport code must be three upper letters. "\
            "Exapmle:'CPH'. You entered {}".format(departure_airport_code)
        incorect_params.append({
            "param": "departure_airport_code",
            "error_msg": error_msg
        })
    if (
        not arrival_airport_code.isalpha()
        or not arrival_airport_code.isupper()
        or len(arrival_airport_code) != 3
            ):
        error_msg = "Arrival airport code must be three upper letters. "\
            "Exapmle:'VAR'. You entered {}".format(arrival_airport_code)
        incorect_params.append({
            "param": "arrival_airport_code",
            "error_msg": error_msg
        })
    dep_date = datetime.strptime(departure_date, "%d.%m.%Y")
    if datetime.today() > dep_date:
        error_msg = "Departure date({}) must be >= today({})".format(
            dep_date.strftime("%d.%m.%Y"),
            datetime.today().strftime("%d.%m.%Y")
            )
        incorect_params.append({
            "param": "departure_date",
            "error_msg": error_msg
            })
    if arrival_date:
        arr_date = datetime.strptime(arrival_date, "%d.%m.%Y")
        if arr_date < dep_date:
            error_msg = "Return date({}) must be >= departure date({})".format(
                arr_date.strftime("%d.%m.%Y"),
                dep_date.strftime("%d.%m.%Y")
            )
            incorect_params.append({
                "param": "arrival_date",
                "error_msg": error_msg
            })
    passengers = int(passengers)
    if passengers < 1 or passengers > 8:
        error_msg = "Passengers count must be from 1 to 8. "\
            "You entered {}".format(passengers)
        incorect_params.append({
            "param": "passengers",
            "error_msg": error_msg
        })
    if len(incorect_params) > 0:
        result = False
    return result, incorect_params


if len(argv) < 4:
    print """You entered <3 parameters.
Please input departure IATA code, arrival IATA code and departure date."""
    exit()
result = scrape(*argv[1:])
if result is None:
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
