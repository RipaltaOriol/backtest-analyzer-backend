import pandas as pd
from app import app
from flask import jsonify

def prettify_table(df):
  # FIX: change the header's name
  # rename headers
  old_columns = df.columns.tolist()
  new_columns = []
  for column in old_columns:
    if '_' in column:
      new_name = column.rsplit('_', 1)[1]
      new_columns.append(new_name)
    elif '.p' == column:
      new_columns.append('Pair')
    else:
      new_columns.append(column)

  df.columns = new_columns
  return df

def get_statistics(df):
  # NOTE: try making the index a column and then convert it to the index
  df.dropna(inplace=True)
  data = {}
  row_indexes = ['Total', 'Mean', 'Count', 'Win-Rate', 'Wins', 'Losses', 'Break-Even', 'Average Win', 'Average Loss', 'Expected Result']
  df_stats = pd.DataFrame(data, index = row_indexes)
  for c in list(df.columns):
    if '.r_' in c:
      # calcultaions
      total = df[c].sum()
      mean = df[c].mean()
      count = df[c].count()
      winners = len(df[(df[c] > 0)])
      lossers = len(df[(df[c] < 0)])
      evens = len(df[(df[c] == 0)])
      df_win = df.loc[(df[c] > 0)]
      df_loss = df.loc[(df[c] < 0)]
      average_win = df_win[c].mean()
      average_loss = df_loss[c].mean()
      win_rate = winners / count
      expected_result = (average_win * (winners / count)) + (average_loss * (lossers / count))
      # creating the new column
      column_name = c.replace('.r_', '')
      new_column = [total, mean, count, win_rate, winners, lossers, evens, average_win, average_loss, expected_result]
      df_stats[column_name] = new_column
  # add index and re-order columns
  df_stats[''] = df_stats.index
  cols = df_stats.columns.tolist()
  cols = cols[-1:] + cols[:-1]
  df_stats = df_stats[cols]
  return df_stats

def get_columns(df):
  # FIX: add authorization to check the file corresponds to the user
  columns = []
  # This way of creating an object is not valid! Use a dictionary!
  for c in list(df.columns):
    if c != '#':
      col = {
        'id': c,
        'dataType': str(df.dtypes[c]),
      }
      # include options if necessary
      if str(df.dtypes[c]) == 'object':
        values = df[c].unique().tolist()
        unique_values = []
        # avoid including 'nan'
        for val in values:
          if (val == val):
            unique_values.append(val)

        col.update({"unique": unique_values})
      if '.m_' in c:
        col.update({"name": c.replace('.m_', '')})
        col.update({"colType": 'metric'})
      if '.r_' in c:
        col.update({"name": c.replace('.r_', '')})
        col.update({"colType": 'result'})
      if '.p' in c:
        col.update({"name": 'Pair'})
        col.update({"colType": 'pair'})

      columns.append(col)

  response = jsonify({'columns': columns})
  return response