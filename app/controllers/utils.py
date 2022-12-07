def parse_column_name(column_name):
    if column_name.startswith('.m_') or column_name.startswith('.r_') or column_name.startswith('.d_'):
      column_name = column_name[3:]
    elif column_name == '.tp':
      column_name = 'Take Profit'
    elif column_name == '.sl':
      column_name = 'Stop Loss'
    elif column_name == '.o':
      column_name = 'Open'
    elif column_name == '.c':
      column_name = 'Close'
    elif column_name == '.p':
      column_name = 'Pair'

    return column_name

def parse_column_type(column_type):
    if column_type == 'object':
        return 'string'
    elif column_type == 'float64' or column_type == 'int64':
        return 'number'
    else:
        return str(column_type)