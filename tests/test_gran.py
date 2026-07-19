import pandas as pd
from config_core.core import rashet_gran, obrabotka_df_posle_zagr


class TestIntegration:
    def test_rashet_gran(self, zagr_df_excel):
        df = zagr_df_excel['df']
        df_tarirovk = zagr_df_excel['df_tarirovk']
        udelka = zagr_df_excel['udelka']

        df_unique, df_duplicates = obrabotka_df_posle_zagr(df)

        df_itog, spisok_otrizat_grani = rashet_gran(df_unique, df_tarirovk, udelka)

        data = {
            'lab_nomer': ['26_00001', '26_00002'],
            'gran_10_%': [0.0, 0.0],
            'gran_5_10_%': [0.0, 0.0],
            'gran_5_2_%': [0.0, 0.0],
            'gran_2_1_%': [0.0, 0.0],
            'gran_1_0_5_%': [0.0, 0.0],
            'gran_0_5_0_25_%': [0.0, 0.0],
            'gran_0_25_0_10_%': [1.6, 1.0],
            'gran_0,10-0,05_%': [7.4, 9.3],
            'gran_0.05-0.01_%': [20.9, 20.6],
            'gran_0.01-0.002_%': [47.1, 46.4],
            'gran_0.002_%': [23.0, 22.7]
        }

        df_test = pd.DataFrame(data)

        assert len(df_test) == len(df_itog)
        assert udelka == 2.7
        pd.testing.assert_frame_equal(df_itog, df_test)