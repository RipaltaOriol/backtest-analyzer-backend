import re

import pandas as pd
from app.utils.math_operations import percentage_change


class StatisticsService:
    def __init__(self):
        pass

    @staticmethod
    def sum_values(column, round_decimals: int = 3):
        # Assuming total needs rounding to 3 decimal places
        return round(column.sum(), round_decimals)

    @staticmethod
    def mean_value(column, round_decimals: int = 3):
        clean_data = column.dropna()
        mean = clean_data.mean()
        return round(mean, round_decimals)

    @staticmethod
    def count_wins(column):
        return (column > 0).sum()

    @staticmethod
    def sum_wins(column):
        return column[column > 0].sum()

    @staticmethod
    def count_losses(column):
        return (column < 0).sum()

    @staticmethod
    def sum_losses(column):
        return column[column < 0].sum()

    @staticmethod
    def count_break_even(column):
        return (column == 0).sum()

    @staticmethod
    def average_win(column, round_decimals: int = 3):
        wins = column[column > 0]
        if not wins.empty:
            return round(wins.mean(), round_decimals)
        return 0

    @staticmethod
    def average_loss(column, round_decimals: int = 3):
        losses = column[column < 0]
        if not losses.empty:
            return round(losses.mean(), round_decimals)
        return 0

    @staticmethod
    def compute_win_rate(wins, total, round_decimals: int = 4):
        win_rate = (wins / total) * 100 if total > 0 else 0
        return round(win_rate, round_decimals)

    @staticmethod
    def calculate_expectancy(
        win_rate, average_win, average_loss, round_decimals: int = 2
    ):
        win_rate = win_rate / 100
        expectancy = (win_rate * average_win) - ((1 - win_rate) * abs(average_loss))
        return round(expectancy, round_decimals)

    @staticmethod
    def max_consecutive_losses(column):
        # Replace None with NaN and filter out non-negative values
        clean_data = column.dropna().lt(0)
        # Calculate consecutive negative groups
        if clean_data.any():  # Check if there are any negative values
            # Identify changes in groups and count them
            return (
                (clean_data != clean_data.shift())
                .cumsum()[clean_data]
                .value_counts()
                .max()
            )
        else:
            return 0

    @staticmethod
    def profit_factor(sum_wins, sum_losses, round_decimals: int = 2):
        if sum_losses == 0:
            return round(sum_wins, round_decimals)
        return round(sum_wins / abs(sum_losses), round_decimals)

    @staticmethod
    def max_value(column, round_decimals: int = 2):
        max_value = column.max()
        return round(max_value, round_decimals) if not pd.isna(max_value) else None

    @staticmethod
    def calculate_drawdown(
        column, round_decimals: int = 3
    ):  # check cuase it probably won't work TODO
        # Convert the series to a DataFrame to hold additional data
        df = pd.DataFrame({"profit": column})
        # Calculate the cumulative maximum to date for each point
        df["cumsum"] = df.profit.cumsum()
        df["high"] = df["cumsum"].cummax()
        # Calculate drawdown: the difference from the cumulative maximum to the current value
        df["drawdown"] = df["cumsum"] - df["high"]
        # The maximum drawdown is the minimum value found in the drawdown series
        max_drawdown = df["drawdown"].min()
        return (
            round(max_drawdown, round_decimals) if not pd.isna(max_drawdown) else None
        )

    def get_dataframe_statistics(self, df):
        cols_result = [col for col in df if re.match(r"col_[vpr]_", col)]

        statistics = {
            col: self.compute_column_statistics(df[col]) for col in cols_result
        }

        return statistics, None

    def compute_column_statistics(self, column):

        count = column.count()
        wins = self.count_wins(column)

        win_rate = self.compute_win_rate(wins, count)

        avg_win = self.average_win(column)
        avg_loss = self.average_loss(column)

        sum_wins = self.sum_wins(column)
        sum_losses = self.sum_losses(column)

        return {
            "count": count,
            "total": self.sum_values(column),
            "mean": self.mean_value(column),
            "wins": wins,
            "losses": self.count_losses(column),
            "breakEven": self.count_break_even(column),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "expectancy": self.calculate_expectancy(win_rate, avg_win, avg_loss),
            "max_consec_loss": self.max_consecutive_losses(column),
            "max_win": self.max_value(column),
            "profit_factor": self.profit_factor(sum_wins, sum_losses),
            "drawdown": self.calculate_drawdown(column),
        }

    def get_calendar_statistics(
        self, df, target_date, target_metric, month, year, timezone_offset
    ):

        df[target_date] = pd.to_datetime(df[target_date]) + pd.Timedelta(
            minutes=-timezone_offset
        )
        df = df.set_index(target_date)
        current_df = df.loc[(df.index.month == month) & (df.index.year == year)]
        if current_df.empty:
            return None, "No data available for the specified month and year."

        previous_month = month - 1 if month > 1 else 12
        previous_year = year - 1 if previous_month == 12 else year
        previous_df = df.loc[
            (df.index.month == previous_month) & (df.index.year == previous_year)
        ]

        current_stats = self.calculate_metrics(current_df[target_metric])
        previous_stats = (
            self.calculate_metrics(previous_df[target_metric])
            if not previous_df.empty
            else {}
        )

        # Calculate percentage differences
        previous_stats_changes = {}
        for key in current_stats:
            previous_stats_changes[key] = percentage_change(
                current_stats[key], previous_stats.get(key, 0)
            )

        response = {
            "current": current_stats,
            "previous": previous_stats_changes,
            "success": True,
        }
        return response, None

    def calculate_metrics(self, data, target_metric: str = None):
        round_decimals = 2

        positive = self.sum_wins(data)
        negative = self.sum_losses(data)

        if target_metric and target_metric.startswith("col_p_"):
            round_decimals = 4
            positive = positive * 100
            negative = negative * 100

        negative = 1 if negative == 0 else negative  # Prevent division by zero

        # Safeguards against NaN values and ensures that the max and min are sensibly calculated
        min_val = round(data.min() if not pd.isna(data.min()) else 0, round_decimals)

        # TODO: validate if we can use round_decimals below
        metrics = {
            "total_trades": len(data),
            "net_pnl": self.sum_values(data, 2),
            "average_profit": self.mean_value(data, round_decimals),
            "max_win": self.max_value(data),
            "max_loss": min_val,
            "wins": self.count_wins(data),
            "losses": self.count_losses(data),
            "breakEvens": self.count_break_even(data),
            "profit_factor": round(positive / abs(negative), 2),
        }

        return metrics
