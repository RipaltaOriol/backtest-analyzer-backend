import numpy as np
import pandas as pd

def apply_filter(df, filter, action, value):
  # FIX: turn into switcher
  if action == 'numericInclude':
    df = filter_numeric_include(filter, value, df)
  elif action == 'numericExclude':
    df = filter_numeric_exclude(filter, value, df)
  elif action == 'numericExclude':
    df = filter_numeric_exclude(filter, value, df)
  elif action == 'bigger':
    df = filter_bigger(filter, value, df)
  elif action == 'smaller':
    df = filter_smaller(filter, value, df)
  elif action == 'range':
    df = filter_range(filter, value, df)
  elif action == 'notRange':
    df = filter_not_range(filter, value, df)
  elif action == 'textInclude':
    df = filter_text_include(filter, value, df)
  elif action == 'textExclude':
    df = filter_text_exclude(filter, value, df)
  
  return df

def filter_numeric_include(field, value, df):
  items = np.array(value)
  items = items.astype(np.float)
  df_filter = df[df[field].isin(items)]
  return df_filter

def filter_numeric_exclude(field, value, df):
  items = np.array(value)
  items = items.astype(np.float)
  df_filter = df[-df[field].isin(items)]
  return df_filter

def filter_bigger(field, value, df):
  value = float(value)
  df_filter = df[df[field] > value]
  return df_filter

def filter_smaller(field, value, df):
  value = float(value)
  df_filter = df[df[field] < value]
  return df_filter

def filter_range(field, value, df):
  range = value.split('/')
  lower = float(range[0])
  upper = float(range[1])
  df_filter = df[(df[field] > lower) & (df[field] < upper)]
  return df_filter

def filter_not_range(field, value, df):
  range = value.split('/')
  lower = float(range[0])
  upper = float(range[1])
  df_filter = df[(df[field] < lower) | (df[field] > upper)]
  return df_filter

def filter_text_include(field, value, df):
  df_filter = df[df[field].isin(value)]
  return df_filter

def filter_text_exclude(field, value, df):
  df_filter = df[-df[field].isin(value)]
  return df_filter