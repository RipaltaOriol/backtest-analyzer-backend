from datetime import datetime

from app.controllers.utils import normalize_results, parse_column_name
from flask import jsonify


def calculate_equity(equity: int, value: int, method: str) -> int:
    """
    Calculates the equity value given a value (next result) and a method.
    """
    if method == "risk_reward":
        return equity + equity * 0.01 * value
    elif method == "percentage":
        return equity + equity * value
    else:  # default method is aboslute profit value
        return equity + value


# TODO: some of this code can be abstracted
def get_line(df, result_columns, current_metric: str) -> str:
    """
    Returns a JSON response that contains the data to create a line chart.
    The current_metric can be 'default' which indicates that no date metric is being used.
    As a result, we will return the trades numbered in the order that they are stored in the database.
    """
    datasets = []
    metric_date = None

    metric_columns = [col for col in df if col.startswith("col_d_")]
    if current_metric in metric_columns or current_metric == "default":
        metric_date = current_metric
    else:
        metric_date = metric_columns[0] if len(metric_columns) > 0 else "default"

    if metric_date == None:
        return "Bad"

    if metric_date != "default":
        df.sort_values(by=[metric_date], inplace=True)

    for column in result_columns:
        if column.startswith("col_v_"):
            method = "value"
        elif column.startswith("col_p_"):
            method = "percentage"
        elif column.startswith("col_r_"):
            method = "risk_reward"

        equity = 10000
        points = []
        for i in range(len(df[column])):
            point = df[column].iloc[i]
            if point is not None:
                equity = calculate_equity(equity, df[column].iloc[i], method)
                points.append(equity)
            else:
                points.append(None)

        datasets.append({"label": column[6:], "data": points})

    axis_label = "Trade Number" if metric_date == "default" else metric_date[6:]

    labels = {"title": "$10.000 Equity Simlutaion", "axes": axis_label}

    if not datasets:
        return jsonify(
            {
                "msg": "No available data yet",
                "success": False,
                "labels": labels,
                "data": datasets,
                "active_metric": metric_date,
                "metric_list": [
                    [metric, parse_column_name(metric)] for metric in metric_columns
                ]
                + [["default", "Trade Number"]],
            }
        )

    x_labels = (
        list(range(1, 1 + len(df[result_columns[0]])))
        if metric_date == "default"
        else df[metric_date].dt.strftime("%d-%m-%Y %H:%M:%S").tolist()
    )

    return jsonify(
        {
            "labels": labels,
            "success": True,
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

    metric_num = None
    metric_list = [
        col
        for col in metric_columns
        if df.dtypes[col] == "int64" or df.dtypes[col] == "float64"
    ]

    if len(result_columns) == 0 or len(metric_list) == 0:
        return jsonify(
            {
                "success": False,
                "msg": "Not enough data to compute",
            }
        )

    if current_metric in metric_columns:
        metric_num = current_metric
    else:
        metric_num = metric_list[0]

    if metric_num == None:
        return "Bad"

    labels = {
        "title": f"{parse_column_name(metric_num)} to Results",
        "axes": parse_column_name(metric_num),
    }
    for res in result_columns:
        dataset = {
            "label": res[6:],
            # "data": [
            #     {
            #         "x": round(float(df.loc[i, metric_num]), 3),
            #         "y": round(float(normalize_results(df.loc[i, res], res)), 3),
            #     }
            #     for i in df.index
            # ],
        }
        dataset_data = []
        for i in df.index:
            result_point = df.loc[i, res]
            metric_point = df.loc[i, metric_num]
            if result_point is not None and metric_point is not None:
                dataset_data.append(
                    {
                        "x": round(float(metric_point), 3),
                        "y": round(float(normalize_results(result_point, res)), 3),
                    }
                )
        dataset["data"] = dataset_data
        data.append(dataset)
    return jsonify(
        {
            "success": True,
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
        return jsonify(
            {
                "success": False,
                "msg": "Not enough data to compute",
            }
        )

    metric_str = None
    metric_list = [col for col in metric_columns if df.dtypes[col] == "object"]

    if current_metric in metric_columns:
        metric_str = current_metric
    else:
        metric_str = metric_list[0]

    if metric_str == None:
        return "Bad"

    labels = {"title": f"{metric_str[6:]} by Result", "axes": metric_str[6:]}

    # thsi column removal is due to conflicts between datetime columns and group
    df = df.loc[:, ~df.columns.str.startswith("col_d_")]
    df_category = df.groupby(metric_str).sum()
    # this can be extracted from unique() but since groupby is already defined it's probably better this way
    data_labels = [label for label in df_category.index]

    for res in result_columns:
        # float parsing is necessary because JSON does not recognize Numpy data types
        data.append(
            {
                "label": res[6:],
                "data": [
                    round(normalize_results(float(df_category.loc[cat, res]), res), 3)
                    for cat in df_category.index
                ],
            }
        )
    return jsonify(
        {
            "success": True,
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
