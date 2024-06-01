import json


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles specific data types and formatting, such as dates and NaN values.
    """

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super(CustomJSONEncoder, self).default(obj)


def serialize_to_json(data):
    """
    Serializes data to JSON format using the CustomJSONEncoder to handle specific data types.
    """
    json_txt = json.dumps(data, cls=CustomJSONEncoder)
    return json.loads(json_txt)
