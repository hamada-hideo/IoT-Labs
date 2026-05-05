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
        if EVENTS_KEY not in k:
            return False
        if BASETIME_KEY in k:
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

def build_array_dict(event_array, basename = None, basetime = None):
    res = {EVENTS_KEY: event_array}
    if basename:
        res[BASENAME_KEY] = basename
    if basetime:
        res[BASETIME_KEY] = basetime
    return res

def flatten_senml(senml_doc):
    """
    Prende in input un dizionario SenML e restituisce una lista di eventi "piatti",
    in cui il base-name (bn) e il base-time (bt) sono stati risolti all'interno 
    di ogni singolo evento.
    """
    flattened_events = []
    
    # Estraiamo bn e bt (con valori di default se non presenti)
    bn = senml_doc.get("bn", "")
    bt = senml_doc.get("bt", 0.0)
    
    for event in senml_doc.get("e", []):
        n = event.get("n", "")
        t = event.get("t", 0.0)
        
        # Creiamo un evento piatto risolvendo le regole IETF SenML
        flat_event = {
            "n": bn + n,      # Nome assoluto della risorsa
            "t": bt + t,      # Timestamp assoluto dell'evento
            "v": event.get("v"),
            "u": event.get("u")
        }
        flattened_events.append(flat_event)
        
    return flattened_events