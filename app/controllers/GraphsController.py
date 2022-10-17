from flask import jsonify
from matplotlib.pyplot import title

def get_scatter(df, result_columns, metric_columns):
    data = []
    
    if len(result_columns) == 0 or len(metric_columns) == 0:
        return 'Bad'

    metric_num = next((col for col in metric_columns if df.dtypes[col] == 'int64' or df.dtypes[col] == 'float64'), None)

    if metric_num == None:
        return 'Bad'

    labels = {
        'title': f'{metric_num[3:]} to Results',
        'axes': metric_num[3:]
    }

    for res in result_columns:
        dataset = {
            'label': res[3:],
            'data': [{'x': round(df.loc[i, metric_num], 3), 'y': round(df.loc[i, res], 3)} for i in df.index]
        }
        data.append(dataset)
    
    return jsonify({
        'data': data,
        'labels': labels
    })

def get_bar(df, result_columns, metric_columns):
    data = []

    if len(result_columns) == 0 or len(metric_columns) == 0:
        return 'Bad'

    metric_str = next((col for col in metric_columns if df.dtypes[col] == 'object'), None)

    if metric_str == None:
        return 'Bad'

    labels = {
        'title': f'{metric_str[3:]} by Result',
        'axes': metric_str[3:]
    }

    df_category = df.groupby(metric_str).sum()

    data_labels = [label for label in df_category.index]

    for res in result_columns:
        data.append({
            'label': res[3:],
            'data': [round(df_category.loc[cat, res], 3) for cat in df_category.index]
        })
    


    return jsonify({
        'data': data,
        'dataLabels': data_labels,
        'labels': labels
    })