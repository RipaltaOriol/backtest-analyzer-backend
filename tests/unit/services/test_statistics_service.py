import pandas as pd
import pytest
from app.services.statistics_service import StatisticsService


@pytest.fixture
def stats_service():
    return StatisticsService()  # Assuming no repository needed or it's mocked


def test_sum_values(stats_service):
    data = pd.Series([100, None, 200, 300, None, -50])
    result = stats_service.sum_values(data)
    assert result == 550, "Should sum non-NA values correctly"


def test_mean_value(stats_service):
    data = pd.Series([100, None, 200, 300, None, -50])
    result = stats_service.mean_value(data)
    assert result == 137.5, "Should average non-NA values correctly"


def test_count_wins(stats_service):
    data = pd.Series([100, -50, 75, -25, 0, 50, None])
    result = stats_service.count_wins(data)
    assert result == 3, "Should count wins correctly"


def test_sum_wins(stats_service):
    data = pd.Series([100, -50, 75, -25, 0, 50, None])
    result = stats_service.sum_wins(data)
    assert result == 225, "Should sum wins correctly"


def test_count_losses(stats_service):
    data = pd.Series([100, -50, 75, -25, 0, 50, None])
    result = stats_service.count_losses(data)
    assert result == 2, "Should count losses correctly"


def test_sum_losses(stats_service):
    data = pd.Series([100, -50, 75, -25, 0, 50, None])
    result = stats_service.sum_losses(data)
    assert result == -75, "Should sum losses correctly"


def test_count_break_even(stats_service):
    data = pd.Series([100, -50, 0, -25, 0, 50, None])
    result = stats_service.count_break_even(data)
    assert result == 2, "Should count break evens correctly"


def test_average_win(stats_service):
    data = pd.Series([100, -50, 200, None, -150, 50])
    result = stats_service.average_win(data)
    expected_avg_win = round((100 + 200 + 50) / 3, 3)
    assert (
        abs(result - expected_avg_win) < 0.01
    ), "Should calculate average win correctly"


def test_average_loss(stats_service):
    data = pd.Series([100, -50, 200, -150, None, 50])
    result = stats_service.average_loss(data)
    expected_avg_loss = round((-150 + -50) / 2, 3)
    assert (
        abs(result - expected_avg_loss) < 0.01
    ), "Should calculate average loss correctly"


def test_win_rate(stats_service):
    data = pd.Series([100, -100, 0, 50, 50])

    count = data.count()
    wins = stats_service.count_wins(data)

    result = stats_service.compute_win_rate(wins, count)
    assert result == 60.0, "Should calculate win rate correctly"


def test_calculate_expectancy(stats_service):
    data = pd.Series([100, -10, -50, 200, -150, None, -20, -30, 50])
    average_win = (100 + 200 + 50) / 3
    average_loss = (-10 - 50 - 150 - 20 - 30) / 5
    expected_expectancy = ((3 / 8) * average_win) - ((5 / 8) * abs(average_loss))

    count = data.count()
    wins = stats_service.count_wins(data)
    win_rate = stats_service.compute_win_rate(wins, count)
    avg_win = stats_service.average_win(data)
    avg_loss = stats_service.average_loss(data)
    result = stats_service.calculate_expectancy(win_rate, avg_win, avg_loss)
    assert (
        abs(result - expected_expectancy) < 0.01
    ), "Should calculate expectedancy correctly"


def test_max_consecutive_losses(stats_service):
    data = pd.Series([100, -10, -50, 200, -150, None, -20, -30, 50])
    result = stats_service.max_consecutive_losses(data)
    assert result == 3, "Should calculate max consecutive losses correctly"


def test_max_value(stats_service):
    data = pd.Series([100, -10, -50, 200, -150, None, -20, -30, 50])
    result = stats_service.max_value(data)
    assert result == 200, "Should calculate max value correctly"


def test_drawdown(stats_service):
    data = pd.Series([100, 20, -30, -25, 40, -50])
    result = stats_service.calculate_drawdown(data)
    assert abs(abs(result) - 65) < 0.01, "Should calculate drawdown correctly"


def test_profit_factor(stats_service):
    data = pd.Series([100, -50, 200, -150, 50])

    total_wins = 100 + 200 + 50
    total_losses = 50 + 150

    sum_wins = stats_service.sum_wins(data)
    sum_losses = stats_service.sum_losses(data)

    expected_profit_factor = round(total_wins / total_losses, 3)
    result = stats_service.profit_factor(sum_wins, sum_losses)
    assert (
        abs(result - expected_profit_factor) < 0.01
    ), "Should calculate profit factor correctly"


def test_get_dataframe_statistics(stats_service):
    data = pd.DataFrame(
        {
            "col_v_profit": [100, 200, -100, 50, -50],
            "col_p_profit %": [1, 2, -1, 0.5, -0.5],
        }
    )
    stats, error = stats_service.get_dataframe_statistics(data)

    # Assertions to verify behavior
    assert error is None
    assert "col_v_profit" in stats
    assert "col_p_profit %" in stats
    assert stats["col_v_profit"]["total"] == 200
    assert stats["col_p_profit %"]["wins"] == 3
