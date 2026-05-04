BASENAME_KEY = "bn"
BASETIME_KEY = "bt"
EVENTS_KEY = "e"
NAME_KEY = "n"
TIME_KEY = "t"
UNIT_KEY = "u"
VALUE_KEY = "v"

def validate_SenML(j):
    try:
        k = j.keys()
        if BASENAME_KEY not in k or EVENTS_KEY not in k or BASETIME_KEY not in k:
            return False
        try:
            float(j[BASETIME_KEY])
        except ValueError:
            return False
        for e in j[EVENTS_KEY]:
            k = e.keys()
            if NAME_KEY not in k or UNIT_KEY not in k or VALUE_KEY not in k or TIME_KEY not in k:
                return False
            try:
                float(e[TIME_KEY])
            except ValueError:
                return False
        return True
    except Exception as e:
        print(e)
        return False

def build_event_dict(name, unit, value, time):
    return {
        NAME_KEY: name,
        UNIT_KEY: unit,
        VALUE_KEY: value,
        TIME_KEY: time
    }

def build_array_dict(basename, basetime, event_array):
    return {
        BASENAME_KEY: basename,
        BASETIME_KEY: basetime,
        EVENTS_KEY: event_array
    }