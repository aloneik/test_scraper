from requests import Session, Request
from datetime import datetime
from lxml import html
from sys import argv
from itertools import product


URL = "https://apps.penguin.bg/fly/quote3.aspx"


def scrape(
    departure_city_code, arrival_city_code,
    departure_date, arrival_date=None, passengers=1
        ):
    user_input = {
        "departure_city_code": departure_city_code,
        "arrival_city_code": arrival_city_code,
        "departure_date": departure_date,
        "arrival_date": arrival_date,
        "passengers": passengers
    }
    if not is_valid_input(**user_input):
        return
    session = Session()
    request = build_request(session, URL, parse_user_input(**user_input))
    # try:
    #     result = parse_response(session.send(request))
    # # TODO find exception types to catch
    # except Exception as e:
    #     print e.message
    #     # check_errors(...)
    out, ret = parse_response(session.send(request))
    return process_flights(out, ret, user_input)


def build_request(session, url, payload=None):
    request = Request("GET", url, params=payload)
    return session.prepare_request(request)


# TODO complete implementation
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
    departure_city_code, arrival_city_code,
    departure_date, arrival_date, passengers
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
        payload["rtdate"] = arrival_date
        del payload["ow"]
        payload["rt"] = ""
    return payload


def process_flights(outgoing_flights, return_flights, user_input):
    outgoing_flights = filter(lambda f: all([
            f["dep_code"] == user_input["departure_city_code"],
            f["arr_code"] == user_input["arrival_city_code"],
            f["dep_time"].date() == datetime.strptime(
                user_input["departure_date"], "%d.%m.%Y"
                ).date()
        ]), outgoing_flights)
    if user_input["arrival_date"] is None:
        return sorted(outgoing_flights, key=lambda f: f["price"])
    return_flights = filter(lambda f: all([
        f["dep_code"] == user_input["arrival_city_code"],
        f["arr_code"] == user_input["departure_city_code"],
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
    departure_city_code, arrival_city_code,
    departure_date, arrival_date, passengers
        ):
    result = True
    dep_date = datetime.strptime(departure_date, "%d.%m.%Y")
    if datetime.today() > dep_date:
        print "Departure date must be >= today"
        result = False
    if arrival_date:
        arr_date = datetime.strptime(arrival_date, "%d.%m.%Y")
        if arr_date < dep_date:
            print "Return date must be >= departure date"
            result = False
    if passengers > 8:
        print "Limit of passengers: 8"
        result = False
    return result


if len(argv) < 4:
    print """You entered <3 parameters.
Please input departure IATA code, arrival IATA code and departure date."""
    # TODO Give a second chance
    exit()
result = scrape(*argv[1:])
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
