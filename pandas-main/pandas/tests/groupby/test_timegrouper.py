""" test with the TimeGrouper / grouping with datetimes """

from datetime import datetime
from io import StringIO

import numpy as np
import pytest
import pytz

import pandas.util._test_decorators as td

import pandas as pd
from pandas import (
    DataFrame,
    DatetimeIndex,
    Index,
    MultiIndex,
    Series,
    Timestamp,
    date_range,
    offsets,
)
import pandas._testing as tm
from pandas.core.groupby.grouper import Grouper
from pandas.core.groupby.ops import BinGrouper


@pytest.fixture
def frame_for_truncated_bingrouper():
    """
    DataFrame used by groupby_with_truncated_bingrouper, made into
    a separate fixture for easier re-use in
    test_groupby_apply_timegrouper_with_nat_apply_squeeze
    """
    df = DataFrame(
        {
            "Quantity": [18, 3, 5, 1, 9, 3],
            "Date": [
                Timestamp(2013, 9, 1, 13, 0),
                Timestamp(2013, 9, 1, 13, 5),
                Timestamp(2013, 10, 1, 20, 0),
                Timestamp(2013, 10, 3, 10, 0),
                pd.NaT,
                Timestamp(2013, 9, 2, 14, 0),
            ],
        }
    )
    return df


@pytest.fixture
def groupby_with_truncated_bingrouper(frame_for_truncated_bingrouper):
    """
    GroupBy object such that gb.grouper is a BinGrouper and
    len(gb.grouper.result_index) < len(gb.grouper.group_keys_seq)

    Aggregations on this groupby should have

        dti = date_range("2013-09-01", "2013-10-01", freq="5D", name="Date")

    As either the index or an index level.
    """
    df = frame_for_truncated_bingrouper

    tdg = Grouper(key="Date", freq="5D")
    gb = df.groupby(tdg)

    # check we're testing the case we're interested in
    assert len(gb.grouper.result_index) != len(gb.grouper.group_keys_seq)

    return gb


class TestGroupBy:
    def test_groupby_with_timegrouper(self):
        # GH 4161
        # TimeGrouper requires a sorted index
        # also verifies that the resultant index has the correct name
        df_original = DataFrame(
            {
                "Buyer": "Carl Carl Carl Carl Joe Carl".split(),
                "Quantity": [18, 3, 5, 1, 9, 3],
                "Date": [
                    datetime(2013, 9, 1, 13, 0),
                    datetime(2013, 9, 1, 13, 5),
                    datetime(2013, 10, 1, 20, 0),
                    datetime(2013, 10, 3, 10, 0),
                    datetime(2013, 12, 2, 12, 0),
                    datetime(2013, 9, 2, 14, 0),
                ],
            }
        )

        # GH 6908 change target column's order
        df_reordered = df_original.sort_values(by="Quantity")

        for df in [df_original, df_reordered]:
            df = df.set_index(["Date"])

            expected = DataFrame(
                {"Buyer": 0, "Quantity": 0},
                index=date_range(
                    "20130901", "20131205", freq="5D", name="Date", inclusive="left"
                ),
            )
            expected.iloc[0, 0] = "CarlCarlCarl"
            expected.iloc[6, 0] = "CarlCarl"
            expected.iloc[18, 0] = "Joe"
            expected.iloc[[0, 6, 18], 1] = np.array([24, 6, 9], dtype="int64")

            msg = "The default value of numeric_only"
            with tm.assert_produces_warning(FutureWarning, match=msg):
                result1 = df.resample("5D").sum()
            tm.assert_frame_equal(result1, expected[["Quantity"]])

            df_sorted = df.sort_index()
            result2 = df_sorted.groupby(Grouper(freq="5D")).sum()
            tm.assert_frame_equal(result2, expected)

            result3 = df.groupby(Grouper(freq="5D")).sum()
            tm.assert_frame_equal(result3, expected)

    @pytest.mark.parametrize("should_sort", [True, False])
    def test_groupby_with_timegrouper_methods(self, should_sort):
        # GH 3881
        # make sure API of timegrouper conforms

        df = DataFrame(
            {
                "Branch": "A A A A A B".split(),
                "Buyer": "Carl Mark Carl Joe Joe Carl".split(),
                "Quantity": [1, 3, 5, 8, 9, 3],
                "Date": [
                    datetime(2013, 1, 1, 13, 0),
                    datetime(2013, 1, 1, 13, 5),
                    datetime(2013, 10, 1, 20, 0),
                    datetime(2013, 10, 2, 10, 0),
                    datetime(2013, 12, 2, 12, 0),
                    datetime(2013, 12, 2, 14, 0),
                ],
            }
        )

        if should_sort:
            df = df.sort_values(by="Quantity", ascending=False)

        df = df.set_index("Date", drop=False)
        g = df.groupby(Grouper(freq="6M"))
        assert g.group_keys

        assert isinstance(g.grouper, BinGrouper)
        groups = g.groups
        assert isinstance(groups, dict)
        assert len(groups) == 3

    def test_timegrouper_with_reg_groups(self):

        # GH 3794
        # allow combination of timegrouper/reg groups

        df_original = DataFrame(
            {
                "Branch": "A A A A A A A B".split(),
                "Buyer": "Carl Mark Carl Carl Joe Joe Joe Carl".split(),
                "Quantity": [1, 3, 5, 1, 8, 1, 9, 3],
                "Date": [
                    datetime(2013, 1, 1, 13, 0),
                    datetime(2013, 1, 1, 13, 5),
                    datetime(2013, 10, 1, 20, 0),
                    datetime(2013, 10, 2, 10, 0),
                    datetime(2013, 10, 1, 20, 0),
                    datetime(2013, 10, 2, 10, 0),
                    datetime(2013, 12, 2, 12, 0),
                    datetime(2013, 12, 2, 14, 0),
                ],
            }
        ).set_index("Date")

        df_sorted = df_original.sort_values(by="Quantity", ascending=False)

        for df in [df_original, df_sorted]:
            expected = DataFrame(
                {
                    "Buyer": "Carl Joe Mark".split(),
                    "Quantity": [10, 18, 3],
                    "Date": [
                        datetime(2013, 12, 31, 0, 0),
                        datetime(2013, 12, 31, 0, 0),
                        datetime(2013, 12, 31, 0, 0),
                    ],
                }
            ).set_index(["Date", "Buyer"])

            msg = "The default value of numeric_only"
            result = df.groupby([Grouper(freq="A"), "Buyer"]).sum(numeric_only=True)
            tm.assert_frame_equal(result, expected)

            expected = DataFrame(
                {
                    "Buyer": "Carl Mark Carl Joe".split(),
                    "Quantity": [1, 3, 9, 18],
                    "Date": [
                        datetime(2013, 1, 1, 0, 0),
                        datetime(2013, 1, 1, 0, 0),
                        datetime(2013, 7, 1, 0, 0),
                        datetime(2013, 7, 1, 0, 0),
                    ],
                }
            ).set_index(["Date", "Buyer"])
            result = df.groupby([Grouper(freq="6MS"), "Buyer"]).sum(numeric_only=True)
            tm.assert_frame_equal(result, expected)

        df_original = DataFrame(
            {
                "Branch": "A A A A A A A B".split(),
                "Buyer": "Carl Mark Carl Carl Joe Joe Joe Carl".split(),
                "Quantity": [1, 3, 5, 1, 8, 1, 9, 3],
                "Date": [
                    datetime(2013, 10, 1, 13, 0),
                    datetime(2013, 10, 1, 13, 5),
                    datetime(2013, 10, 1, 20, 0),
                    datetime(2013, 10, 2, 10, 0),
                    datetime(2013, 10, 1, 20, 0),
                    datetime(2013, 10, 2, 10, 0),
                    datetime(2013, 10, 2, 12, 0),
                    datetime(2013, 10, 2, 14, 0),
                ],
            }
        ).set_index("Date")

        df_sorted = df_original.sort_values(by="Quantity", ascending=False)
        for df in [df_original, df_sorted]:

            expected = DataFrame(
                {
                    "Buyer": "Carl Joe Mark Carl Joe".split(),
                    "Quantity": [6, 8, 3, 4, 10],
                    "Date": [
                        datetime(2013, 10, 1, 0, 0),
                        datetime(2013, 10, 1, 0, 0),
                        datetime(2013, 10, 1, 0, 0),
                        datetime(2013, 10, 2, 0, 0),
                        datetime(2013, 10, 2, 0, 0),
                    ],
                }
            ).set_index(["Date", "Buyer"])

            result = df.groupby([Grouper(freq="1D"), "Buyer"]).sum(numeric_only=True)
            tm.assert_frame_equal(result, expected)

            result = df.groupby([Grouper(freq="1M"), "Buyer"]).sum(numeric_only=True)
            expected = DataFrame(
                {
                    "Buyer": "Carl Joe Mark".split(),
                    "Quantity": [10, 18, 3],
                    "Date": [
                        datetime(2013, 10, 31, 0, 0),
                        datetime(2013, 10, 31, 0, 0),
                        datetime(2013, 10, 31, 0, 0),
                    ],
                }
            ).set_index(["Date", "Buyer"])
            tm.assert_frame_equal(result, expected)

            # passing the name
            df = df.reset_index()
            result = df.groupby([Grouper(freq="1M", key="Date"), "Buyer"]).sum(
                numeric_only=True
            )
            tm.assert_frame_equal(result, expected)

            with pytest.raises(KeyError, match="'The grouper name foo is not found'"):
                df.groupby([Grouper(freq="1M", key="foo"), "Buyer"]).sum()

            # passing the level
            df = df.set_index("Date")
            result = df.groupby([Grouper(freq="1M", level="Date"), "Buyer"]).sum(
                numeric_only=True
            )
            tm.assert_frame_equal(result, expected)
            result = df.groupby([Grouper(freq="1M", level=0), "Buyer"]).sum(
                numeric_only=True
            )
            tm.assert_frame_equal(result, expected)

            with pytest.raises(ValueError, match="The level foo is not valid"):
                df.groupby([Grouper(freq="1M", level="foo"), "Buyer"]).sum()

            # multi names
            df = df.copy()
            df["Date"] = df.index + offsets.MonthEnd(2)
            result = df.groupby([Grouper(freq="1M", key="Date"), "Buyer"]).sum(
                numeric_only=True
            )
            expected = DataFrame(
                {
                    "Buyer": "Carl Joe Mark".split(),
                    "Quantity": [10, 18, 3],
                    "Date": [
                        datetime(2013, 11, 30, 0, 0),
                        datetime(2013, 11, 30, 0, 0),
                        datetime(2013, 11, 30, 0, 0),
                    ],
                }
            ).set_index(["Date", "Buyer"])
            tm.assert_frame_equal(result, expected)

            # error as we have both a level and a name!
            msg = "The Grouper cannot specify both a key and a level!"
            with pytest.raises(ValueError, match=msg):
                df.groupby(
                    [Grouper(freq="1M", key="Date", level="Date"), "Buyer"]
                ).sum()

            # single groupers
            expected = DataFrame(
                [[31]],
                columns=["Quantity"],
                index=DatetimeIndex(
                    [datetime(2013, 10, 31, 0, 0)], freq=offsets.MonthEnd(), name="Date"
                ),
            )
            result = df.groupby(Grouper(freq="1M")).sum(numeric_only=True)
            tm.assert_frame_equal(result, expected)

            result = df.groupby([Grouper(freq="1M")]).sum(numeric_only=True)
            tm.assert_frame_equal(result, expected)

            expected.index = expected.index.shift(1)
            assert expected.index.freq == offsets.MonthEnd()
            result = df.groupby(Grouper(freq="1M", key="Date")).sum(numeric_only=True)
            tm.assert_frame_equal(result, expected)

            result = df.groupby([Grouper(freq="1M", key="Date")]).sum(numeric_only=True)
            tm.assert_frame_equal(result, expected)

    @pytest.mark.parametrize("freq", ["D", "M", "A", "Q-APR"])
    def test_timegrouper_with_reg_groups_freq(self, freq):
        # GH 6764 multiple grouping with/without sort
        df = DataFrame(
            {
                "date": pd.to_datetime(
                    [
                        "20121002",
                        "20121007",
                        "20130130",
                        "20130202",
                        "20130305",
                        "20121002",
                        "20121207",
                        "20130130",
                        "20130202",
                        "20130305",
                        "20130202",
                        "20130305",
                    ]
                ),
                "user_id": [1, 1, 1, 1, 1, 3, 3, 3, 5, 5, 5, 5],
                "whole_cost": [
                    1790,
                    364,
                    280,
                    259,
                    201,
                    623,
                    90,
                    312,
                    359,
                    301,
                    359,
                    801,
                ],
                "cost1": [12, 15, 10, 24, 39, 1, 0, 90, 45, 34, 1, 12],
            }
        ).set_index("date")

        expected = (
            df.groupby("user_id")["whole_cost"]
            .resample(freq)
            .sum(min_count=1)  # XXX
            .dropna()
            .reorder_levels(["date", "user_id"])
            .sort_index()
            .astype("int64")
        )
        expected.name = "whole_cost"

        result1 = (
            df.sort_index().groupby([Grouper(freq=freq), "user_id"])["whole_cost"].sum()
        )
        tm.assert_series_equal(result1, expected)

        result2 = df.groupby([Grouper(freq=freq), "user_id"])["whole_cost"].sum()
        tm.assert_series_equal(result2, expected)

    def test_timegrouper_get_group(self):
        # GH 6914

        df_original = DataFrame(
            {
                "Buyer": "Carl Joe Joe Carl Joe Carl".split(),
                "Quantity": [18, 3, 5, 1, 9, 3],
                "Date": [
                    datetime(2013, 9, 1, 13, 0),
                    datetime(2013, 9, 1, 13, 5),
                    datetime(2013, 10, 1, 20, 0),
                    datetime(2013, 10, 3, 10, 0),
                    datetime(2013, 12, 2, 12, 0),
                    datetime(2013, 9, 2, 14, 0),
                ],
            }
        )
        df_reordered = df_original.sort_values(by="Quantity")

        # single grouping
        expected_list = [
            df_original.iloc[[0, 1, 5]],
            df_original.iloc[[2, 3]],
            df_original.iloc[[4]],
        ]
        dt_list = ["2013-09-30", "2013-10-31", "2013-12-31"]

        for df in [df_original, df_reordered]:
            grouped = df.groupby(Grouper(freq="M", key="Date"))
            for t, expected in zip(dt_list, expected_list):
                dt = Timestamp(t)
                result = grouped.get_group(dt)
                tm.assert_frame_equal(result, expected)

        # multiple grouping
        expected_list = [
            df_original.iloc[[1]],
            df_original.iloc[[3]],
            df_original.iloc[[4]],
        ]
        g_list = [("Joe", "2013-09-30"), ("Carl", "2013-10-31"), ("Joe", "2013-12-31")]

        for df in [df_original, df_reordered]:
            grouped = df.groupby(["Buyer", Grouper(freq="M", key="Date")])
            for (b, t), expected in zip(g_list, expected_list):
                dt = Timestamp(t)
                result = grouped.get_group((b, dt))
                tm.assert_frame_equal(result, expected)

        # with index
        df_original = df_original.set_index("Date")
        df_reordered = df_original.sort_values(by="Quantity")

        expected_list = [
            df_original.iloc[[0, 1, 5]],
            df_original.iloc[[2, 3]],
            df_original.iloc[[4]],
        ]

        for df in [df_original, df_reordered]:
            grouped = df.groupby(Grouper(freq="M"))
            for t, expected in zip(dt_list, expected_list):
                dt = Timestamp(t)
                result = grouped.get_group(dt)
                tm.assert_frame_equal(result, expected)

    def test_timegrouper_apply_return_type_series(self):
        # Using `apply` with the `TimeGrouper` should give the
        # same return type as an `apply` with a `Grouper`.
        # Issue #11742
        df = DataFrame({"date": ["10/10/2000", "11/10/2000"], "value": [10, 13]})
        df_dt = df.copy()
        df_dt["date"] = pd.to_datetime(df_dt["date"])

        def sumfunc_series(x):
            return Series([x["value"].sum()], ("sum",))

        expected = df.groupby(Grouper(key="date")).apply(sumfunc_series)
        result = df_dt.groupby(Grouper(freq="M", key="date")).apply(sumfunc_series)
        tm.assert_frame_equal(
            result.reset_index(drop=True), expected.reset_index(drop=True)
        )

    def test_timegrouper_apply_return_type_value(self):
        # Using `apply` with the `TimeGrouper` should give the
        # same return type as an `apply` with a `Grouper`.
        # Issue #11742
        df = DataFrame({"date": ["10/10/2000", "11/10/2000"], "value": [10, 13]})
        df_dt = df.copy()
        df_dt["date"] = pd.to_datetime(df_dt["date"])

        def sumfunc_value(x):
            return x.value.sum()

        expected = df.groupby(Grouper(key="date")).apply(sumfunc_value)
        result = df_dt.groupby(Grouper(freq="M", key="date")).apply(sumfunc_value)
        tm.assert_series_equal(
            result.reset_index(drop=True), expected.reset_index(drop=True)
        )

    def test_groupby_groups_datetimeindex(self):
        # GH#1430
        periods = 1000
        ind = date_range(start="2012/1/1", freq="5min", periods=periods)
        df = DataFrame(
            {"high": np.arange(periods), "low": np.arange(periods)}, index=ind
        )
        grouped = df.groupby(lambda x: datetime(x.year, x.month, x.day))

        # it works!
        groups = grouped.groups
        assert isinstance(list(groups.keys())[0], datetime)

        # GH#11442
        index = date_range("2015/01/01", periods=5, name="date")
        df = DataFrame({"A": [5, 6, 7, 8, 9], "B": [1, 2, 3, 4, 5]}, index=index)
        result = df.groupby(level="date").groups
        dates = ["2015-01-05", "2015-01-04", "2015-01-03", "2015-01-02", "2015-01-01"]
        expected = {
            Timestamp(date): DatetimeIndex([date], name="date") for date in dates
        }
        tm.assert_dict_equal(result, expected)

        grouped = df.groupby(level="date")
        for date in dates:
            result = grouped.get_group(date)
            data = [[df.loc[date, "A"], df.loc[date, "B"]]]
            expected_index = DatetimeIndex([date], name="date", freq="D")
            expected = DataFrame(data, columns=list("AB"), index=expected_index)
            tm.assert_frame_equal(result, expected)

    def test_groupby_groups_datetimeindex_tz(self):
        # GH 3950
        dates = [
            "2011-07-19 07:00:00",
            "2011-07-19 08:00:00",
            "2011-07-19 09:00:00",
            "2011-07-19 07:00:00",
            "2011-07-19 08:00:00",
            "2011-07-19 09:00:00",
        ]
        df = DataFrame(
            {
                "label": ["a", "a", "a", "b", "b", "b"],
                "datetime": dates,
                "value1": np.arange(6, dtype="int64"),
                "value2": [1, 2] * 3,
            }
        )
        df["datetime"] = df["datetime"].apply(lambda d: Timestamp(d, tz="US/Pacific"))

        exp_idx1 = DatetimeIndex(
            [
                "2011-07-19 07:00:00",
                "2011-07-19 07:00:00",
                "2011-07-19 08:00:00",
                "2011-07-19 08:00:00",
                "2011-07-19 09:00:00",
                "2011-07-19 09:00:00",
            ],
            tz="US/Pacific",
            name="datetime",
        )
        exp_idx2 = Index(["a", "b"] * 3, name="label")
        exp_idx = MultiIndex.from_arrays([exp_idx1, exp_idx2])
        expected = DataFrame(
            {"value1": [0, 3, 1, 4, 2, 5], "value2": [1, 2, 2, 1, 1, 2]},
            index=exp_idx,
            columns=["value1", "value2"],
        )

        result = df.groupby(["datetime", "label"]).sum()
        tm.assert_frame_equal(result, expected)

        # by level
        didx = DatetimeIndex(dates, tz="Asia/Tokyo")
        df = DataFrame(
            {"value1": np.arange(6, dtype="int64"), "value2": [1, 2, 3, 1, 2, 3]},
            index=didx,
        )

        exp_idx = DatetimeIndex(
            ["2011-07-19 07:00:00", "2011-07-19 08:00:00", "2011-07-19 09:00:00"],
            tz="Asia/Tokyo",
        )
        expected = DataFrame(
            {"value1": [3, 5, 7], "value2": [2, 4, 6]},
            index=exp_idx,
            columns=["value1", "value2"],
        )

        result = df.groupby(level=0).sum()
        tm.assert_frame_equal(result, expected)

    def test_frame_datetime64_handling_groupby(self):
        # it works!
        df = DataFrame(
            [(3, np.datetime64("2012-07-03")), (3, np.datetime64("2012-07-04"))],
            columns=["a", "date"],
        )
        result = df.groupby("a").first()
        assert result["date"][3] == Timestamp("2012-07-03")

    def test_groupby_multi_timezone(self):

        # combining multiple / different timezones yields UTC

        data = """0,2000-01-28 16:47:00,America/Chicago
1,2000-01-29 16:48:00,America/Chicago
2,2000-01-30 16:49:00,America/Los_Angeles
3,2000-01-31 16:50:00,America/Chicago
4,2000-01-01 16:50:00,America/New_York"""

        df = pd.read_csv(StringIO(data), header=None, names=["value", "date", "tz"])
        result = df.groupby("tz", group_keys=False).date.apply(
            lambda x: pd.to_datetime(x).dt.tz_localize(x.name)
        )

        expected = Series(
            [
                Timestamp("2000-01-28 16:47:00-0600", tz="America/Chicago"),
                Timestamp("2000-01-29 16:48:00-0600", tz="America/Chicago"),
                Timestamp("2000-01-30 16:49:00-0800", tz="America/Los_Angeles"),
                Timestamp("2000-01-31 16:50:00-0600", tz="America/Chicago"),
                Timestamp("2000-01-01 16:50:00-0500", tz="America/New_York"),
            ],
            name="date",
            dtype=object,
        )
        tm.assert_series_equal(result, expected)

        tz = "America/Chicago"
        res_values = df.groupby("tz").date.get_group(tz)
        result = pd.to_datetime(res_values).dt.tz_localize(tz)
        exp_values = Series(
            ["2000-01-28 16:47:00", "2000-01-29 16:48:00", "2000-01-31 16:50:00"],
            index=[0, 1, 3],
            name="date",
        )
        expected = pd.to_datetime(exp_values).dt.tz_localize(tz)
        tm.assert_series_equal(result, expected)

    def test_groupby_groups_periods(self):
        dates = [
            "2011-07-19 07:00:00",
            "2011-07-19 08:00:00",
            "2011-07-19 09:00:00",
            "2011-07-19 07:00:00",
            "2011-07-19 08:00:00",
            "2011-07-19 09:00:00",
        ]
        df = DataFrame(
            {
                "label": ["a", "a", "a", "b", "b", "b"],
                "period": [pd.Period(d, freq="H") for d in dates],
                "value1": np.arange(6, dtype="int64"),
                "value2": [1, 2] * 3,
            }
        )

        exp_idx1 = pd.PeriodIndex(
            [
                "2011-07-19 07:00:00",
                "2011-07-19 07:00:00",
                "2011-07-19 08:00:00",
                "2011-07-19 08:00:00",
                "2011-07-19 09:00:00",
                "2011-07-19 09:00:00",
            ],
            freq="H",
            name="period",
        )
        exp_idx2 = Index(["a", "b"] * 3, name="label")
        exp_idx = MultiIndex.from_arrays([exp_idx1, exp_idx2])
        expected = DataFrame(
            {"value1": [0, 3, 1, 4, 2, 5], "value2": [1, 2, 2, 1, 1, 2]},
            index=exp_idx,
            columns=["value1", "value2"],
        )

        result = df.groupby(["period", "label"]).sum()
        tm.assert_frame_equal(result, expected)

        # by level
        didx = pd.PeriodIndex(dates, freq="H")
        df = DataFrame(
            {"value1": np.arange(6, dtype="int64"), "value2": [1, 2, 3, 1, 2, 3]},
            index=didx,
        )

        exp_idx = pd.PeriodIndex(
            ["2011-07-19 07:00:00", "2011-07-19 08:00:00", "2011-07-19 09:00:00"],
            freq="H",
        )
        expected = DataFrame(
            {"value1": [3, 5, 7], "value2": [2, 4, 6]},
            index=exp_idx,
            columns=["value1", "value2"],
        )

        result = df.groupby(level=0).sum()
        tm.assert_frame_equal(result, expected)

    def test_groupby_first_datetime64(self):
        df = DataFrame([(1, 1351036800000000000), (2, 1351036800000000000)])
        df[1] = df[1].view("M8[ns]")

        assert issubclass(df[1].dtype.type, np.datetime64)

        result = df.groupby(level=0).first()
        got_dt = result[1].dtype
        assert issubclass(got_dt.type, np.datetime64)

        result = df[1].groupby(level=0).first()
        got_dt = result.dtype
        assert issubclass(got_dt.type, np.datetime64)

    def test_groupby_max_datetime64(self):
        # GH 5869
        # datetimelike dtype conversion from int
        df = DataFrame({"A": Timestamp("20130101"), "B": np.arange(5)})
        expected = df.groupby("A")["A"].apply(lambda x: x.max())
        result = df.groupby("A")["A"].max()
        tm.assert_series_equal(result, expected)

    def test_groupby_datetime64_32_bit(self):
        # GH 6410 / numpy 4328
        # 32-bit under 1.9-dev indexing issue

        df = DataFrame({"A": range(2), "B": [Timestamp("2000-01-1")] * 2})
        result = df.groupby("A")["B"].transform(min)
        expected = Series([Timestamp("2000-01-1")] * 2, name="B")
        tm.assert_series_equal(result, expected)

    def test_groupby_with_timezone_selection(self):
        # GH 11616
        # Test that column selection returns output in correct timezone.
        np.random.seed(42)
        df = DataFrame(
            {
                "factor": np.random.randint(0, 3, size=60),
                "time": date_range("01/01/2000 00:00", periods=60, freq="s", tz="UTC"),
            }
        )
        df1 = df.groupby("factor").max()["time"]
        df2 = df.groupby("factor")["time"].max()
        tm.assert_series_equal(df1, df2)

    def test_timezone_info(self):
        # see gh-11682: Timezone info lost when broadcasting
        # scalar datetime to DataFrame

        df = DataFrame({"a": [1], "b": [datetime.now(pytz.utc)]})
        assert df["b"][0].tzinfo == pytz.utc
        df = DataFrame({"a": [1, 2, 3]})
        df["b"] = datetime.now(pytz.utc)
        assert df["b"][0].tzinfo == pytz.utc

    def test_datetime_count(self):
        df = DataFrame(
            {"a": [1, 2, 3] * 2, "dates": date_range("now", periods=6, freq="T")}
        )
        result = df.groupby("a").dates.count()
        expected = Series([2, 2, 2], index=Index([1, 2, 3], name="a"), name="dates")
        tm.assert_series_equal(result, expected)

    def test_first_last_max_min_on_time_data(self):
        # GH 10295
        # Verify that NaT is not in the result of max, min, first and last on
        # Dataframe with datetime or timedelta values.
        from datetime import timedelta as td

        df_test = DataFrame(
            {
                "dt": [
                    np.nan,
                    "2015-07-24 10:10",
                    "2015-07-25 11:11",
                    "2015-07-23 12:12",
                    np.nan,
                ],
                "td": [np.nan, td(days=1), td(days=2), td(days=3), np.nan],
            }
        )
        df_test.dt = pd.to_datetime(df_test.dt)
        df_test["group"] = "A"
        df_ref = df_test[df_test.dt.notna()]

        grouped_test = df_test.groupby("group")
        grouped_ref = df_ref.groupby("group")

        tm.assert_frame_equal(grouped_ref.max(), grouped_test.max())
        tm.assert_frame_equal(grouped_ref.min(), grouped_test.min())
        tm.assert_frame_equal(grouped_ref.first(), grouped_test.first())
        tm.assert_frame_equal(grouped_ref.last(), grouped_test.last())

    def test_nunique_with_timegrouper_and_nat(self):
        # GH 17575
        test = DataFrame(
            {
                "time": [
                    Timestamp("2016-06-28 09:35:35"),
                    pd.NaT,
                    Timestamp("2016-06-28 16:46:28"),
                ],
                "data": ["1", "2", "3"],
            }
        )

        grouper = Grouper(key="time", freq="h")
        result = test.groupby(grouper)["data"].nunique()
        expected = test[test.time.notnull()].groupby(grouper)["data"].nunique()
        expected.index = expected.index._with_freq(None)
        tm.assert_series_equal(result, expected)

    def test_scalar_call_versus_list_call(self):
        # Issue: 17530
        data_frame = {
            "location": ["shanghai", "beijing", "shanghai"],
            "time": Series(
                ["2017-08-09 13:32:23", "2017-08-11 23:23:15", "2017-08-11 22:23:15"],
                dtype="datetime64[ns]",
            ),
            "value": [1, 2, 3],
        }
        data_frame = DataFrame(data_frame).set_index("time")
        grouper = Grouper(freq="D")

        grouped = data_frame.groupby(grouper)
        result = grouped.count()
        grouped = data_frame.groupby([grouper])
        expected = grouped.count()

        tm.assert_frame_equal(result, expected)

    def test_grouper_period_index(self):
        # GH 32108
        periods = 2
        index = pd.period_range(
            start="2018-01", periods=periods, freq="M", name="Month"
        )
        period_series = Series(range(periods), index=index)
        result = period_series.groupby(period_series.index.month).sum()

        expected = Series(
            range(0, periods), index=Index(range(1, periods + 1), name=index.name)
        )
        tm.assert_series_equal(result, expected)

    def test_groupby_apply_timegrouper_with_nat_dict_returns(
        self, groupby_with_truncated_bingrouper
    ):
        # GH#43500 case where gb.grouper.result_index and gb.grouper.group_keys_seq
        #  have different lengths that goes through the `isinstance(values[0], dict)`
        #  path
        gb = groupby_with_truncated_bingrouper

        res = gb["Quantity"].apply(lambda x: {"foo": len(x)})

        dti = date_range("2013-09-01", "2013-10-01", freq="5D", name="Date")
        mi = MultiIndex.from_arrays([dti, ["foo"] * len(dti)])
        expected = Series([3, 0, 0, 0, 0, 0, 2], index=mi, name="Quantity")
        tm.assert_series_equal(res, expected)

    def test_groupby_apply_timegrouper_with_nat_scalar_returns(
        self, groupby_with_truncated_bingrouper
    ):
        # GH#43500 Previously raised ValueError bc used index with incorrect
        #  length in wrap_applied_result
        gb = groupby_with_truncated_bingrouper

        res = gb["Quantity"].apply(lambda x: x.iloc[0] if len(x) else np.nan)

        dti = date_range("2013-09-01", "2013-10-01", freq="5D", name="Date")
        expected = Series(
            [18, np.nan, np.nan, np.nan, np.nan, np.nan, 5],
            index=dti._with_freq(None),
            name="Quantity",
        )

        tm.assert_series_equal(res, expected)

    def test_groupby_apply_timegrouper_with_nat_apply_squeeze(
        self, frame_for_truncated_bingrouper
    ):
        df = frame_for_truncated_bingrouper

        # We need to create a GroupBy object with only one non-NaT group,
        #  so use a huge freq so that all non-NaT dates will be grouped together
        tdg = Grouper(key="Date", freq="100Y")
        gb = df.groupby(tdg)

        # check that we will go through the singular_series path
        #  in _wrap_applied_output_series
        assert gb.ngroups == 1
        assert gb._selected_obj._get_axis(gb.axis).nlevels == 1

        # function that returns a Series
        res = gb.apply(lambda x: x["Quantity"] * 2)

        expected = DataFrame(
            [[36, 6, 6, 10, 2]],
            index=Index([Timestamp("2013-12-31")], name="Date"),
            columns=Index([0, 1, 5, 2, 3], name="Quantity"),
        )
        tm.assert_frame_equal(res, expected)

    @td.skip_if_no("numba")
    def test_groupby_agg_numba_timegrouper_with_nat(
        self, groupby_with_truncated_bingrouper
    ):
        # See discussion in GH#43487
        gb = groupby_with_truncated_bingrouper

        result = gb["Quantity"].aggregate(
            lambda values, index: np.nanmean(values), engine="numba"
        )

        expected = gb["Quantity"].aggregate(np.nanmean)
        tm.assert_series_equal(result, expected)

        result_df = gb[["Quantity"]].aggregate(
            lambda values, index: np.nanmean(values), engine="numba"
        )
        expected_df = gb[["Quantity"]].aggregate(np.nanmean)
        tm.assert_frame_equal(result_df, expected_df)