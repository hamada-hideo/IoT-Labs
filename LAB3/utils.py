ROOMS = ["living_room", "kitchen", "bedroom"]

def validate_SenML(j):
    try:
        if "bn" not in j.keys() or "e" not in j.keys():
            return False
        for e in j["e"]:
            if "n" not in e.keys() or "u" not in e.keys() or "v" not in e.keys():
                return False
        return True
    except Exception as e:
        return False
