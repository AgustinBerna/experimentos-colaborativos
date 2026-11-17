import unittest
import polars as pl
from ff_variants import forward_fill, fill_remaining, training_medians


class ImputationTests(unittest.TestCase):
    def setUp(self):
        self.df = pl.DataFrame({
            "id": [1, 1, 1, 1, 2, 2],
            "month": [3, 4, 5, 10, 3, 10],
            "x": [None, 100.0, None, 999.0, None, 0.0],
            "target": [0, 1, 0, 1, 0, 1],
        })

    def test_forward_fill_uses_only_same_client_past(self):
        ff = forward_fill(self.df, ["x"], "id", "month")
        self.assertEqual(ff["x"].to_list(), [None, 100, 100, 999, None, 0])

    def test_future_values_cannot_change_past(self):
        altered = self.df.with_columns(
            pl.when(pl.col("month") == 10).then(-10000).otherwise(pl.col("x")).alias("x"))
        past = lambda d: forward_fill(d, ["x"], "id", "month").filter(pl.col("month") < 10)
        self.assertTrue(past(self.df).equals(past(altered)))

    def test_zero_fills_remaining_only_and_preserves_metadata(self):
        ff = forward_fill(self.df, ["x"], "id", "month")
        result = fill_remaining(ff, ["x"], "zero")
        self.assertEqual(result["x"].to_list(), [0, 100, 100, 999, 0, 0])
        self.assertTrue(result.drop("x").equals(ff.drop("x")))

    def test_median_uses_original_train_not_test(self):
        med = training_medians(self.df, ["x"], "month", [3, 4, 5])
        self.assertEqual(med["x"], 100)
        result = fill_remaining(forward_fill(self.df, ["x"], "id", "month"), ["x"], "median", med)
        self.assertEqual(result["x"].to_list(), [100, 100, 100, 999, 100, 0])

    def test_fractional_median_and_all_null_feature(self):
        df = pl.DataFrame({"id": [1, 1, 1], "month": [3, 4, 10],
                           "x": [1, 2, None], "empty": [None, None, None]})
        med = training_medians(df, ["x", "empty"], "month", [3, 4])
        self.assertEqual(med["x"], 1.5)
        result = fill_remaining(df, ["x", "empty"], "median", med)
        self.assertEqual(result["x"].to_list(), [1, 2, 1.5])
        self.assertEqual(result["empty"].null_count(), 3)


if __name__ == "__main__":
    unittest.main()
