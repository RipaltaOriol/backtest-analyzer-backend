from datetime import datetime

from app.controllers.utils import parse_column_name
from flask import jsonify


# TODO: some of this code can be abstracted
def get_line(df, result_columns, current_metric: str) -> str:
    """
    Returns a JSON response that contains the data to create a line chart.
    The current_metric can be 'default' which indicates that no date metric is being used.
    As a result, we will return the trades numbered in the order that they are stored in the database.
    """
    equity = 10000
    datasets = []
    metric_date = None

    metric_columns = [col for col in df if col.startswith("col_d_")]
    if current_metric in metric_columns or current_metric == "default":
        metric_date = current_metric
    else:
        metric_date = metric_columns[0] if len(metric_columns) > 0 else "default"

    if metric_date == None:
        return "Bad"

    for column in result_columns:
        equity = 1000
        points = []
        for i in range(len(df[column])):
            if i == 0:
                points.append(equity + equity * 0.01 * df[column].iloc[i])
            else:
                points.append(points[i - 1] + points[i - 1] * 0.01 * df[column].iloc[i])
        datasets.append({"label": column[6:], "data": points})

    axis_label = "Trade Number" if metric_date == "default" else metric_date[6:]

    labels = {"title": "$" + str(equity) + " Equity Simlutaion", "axes": axis_label}

    x_labels = (
        list(range(1, 1 + len(df[result_columns[0]])))
        if metric_date == "default"
        else df[metric_date].tolist()
    )

    return jsonify(
        {
            "labels": labels,
            "xLabels": x_labels,
            "data": datasets,
            "active_metric": metric_date,
            "metric_list": [
                [metric, parse_column_name(metric)] for metric in metric_columns
            ]
            + [["default", "Trade Number"]],
        }
    )


def get_scatter(df, result_columns, metric_columns, current_metric: str) -> str:
    data = []

    if len(result_columns) == 0 or len(metric_columns) == 0:
        return "Bad"

    metric_num = None
    metric_list = [
        col
        for col in metric_columns
        if df.dtypes[col] == "int64" or df.dtypes[col] == "float64"
    ]

    if current_metric in metric_columns:
        metric_num = current_metric
    else:
        metric_num = metric_list[0]

    if metric_num == None:
        return "Bad"

    labels = {"title": f"{metric_num[6:]} to Results", "axes": metric_num[6:]}

    for res in result_columns:
        dataset = {
            "label": res[6:],
            "data": [
                {
                    "x": round(float(df.loc[i, metric_num]), 3),
                    "y": round(float(df.loc[i, res]), 3),
                }
                for i in df.index
            ],
        }
        data.append(dataset)

    return jsonify(
        {
            "data": data,
            "labels": labels,
            "active_metric": metric_num,
            "metric_list": [
                [metric, parse_column_name(metric)] for metric in metric_list
            ],
        }
    )


def get_bar(df, result_columns, metric_columns, current_metric: str):
    data = []

    if len(result_columns) == 0 or len(metric_columns) == 0:
        return "Bad"

    metric_str = None
    metric_list = [col for col in metric_columns if df.dtypes[col] == "object"]

    if current_metric in metric_columns:
        metric_str = current_metric
    else:
        metric_str = metric_list[0]

    if metric_str == None:
        return "Bad"

    labels = {"title": f"{metric_str[6:]} by Result", "axes": metric_str[6:]}

    df_category = df.groupby(metric_str).sum()

    data_labels = [label for label in df_category.index]

    for res in result_columns:
        data.append(
            {
                "label": res[6:],
                "data": [
                    round(df_category.loc[cat, res], 3) for cat in df_category.index
                ],
            }
        )

    return jsonify(
        {
            "data": data,
            "dataLabels": data_labels,
            "labels": labels,
            "active_metric": metric_str,
            "metric_list": [
                [metric, parse_column_name(metric)] for metric in metric_list
            ],
        }
    )


def get_pie(df, result_column):

    pie = {
        "data": [
            len(df[df[result_column[0]] > 0]),
            len(df[df[result_column[0]] == 0]),
            len(df[df[result_column[0]] < 0]),
        ]
    }

    return jsonify(
        {
            "title": result_column[0][6:] + " by Outcome Distribution",
            "data": [pie],
            "labels": ["Winners", "Break-Even", "Lossers"],
        }
    )
