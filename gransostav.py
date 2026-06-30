import pandas as pd
import config
from vspomogat_func import process_multiheader_column


class RaschetGranov:

    @staticmethod
    def zagr_excel(path):
        df = pd.read_excel(
            path,
            sheet_name="Грансост_кр_расс_с_пром",
            skiprows=4,
            header=[0, 1, 2, 3, 4],
            na_values="-"
        )

        df.columns = [process_multiheader_column(col) for col in df.columns]

        df = df.rename(columns=config.RENAME_COLUMNS_EXCEL)
        df = df[config.RENAME_COLUMNS_EXCEL.values()]

        df = df.dropna(subset=['lab_nomer', "m_do_promiv"])
        df = df.fillna(0)

        return df

    @staticmethod
    def raschet_gran_pesk(df):
        df['gran_10'] = df['m_10']/df['m_do_promiv'] * 100
        df['gran_5_10'] = df['m_10_5']/df['m_do_promiv'] * 100
        df['gran_5_2'] = df['m_5_2']/df['m_do_promiv'] * 100
        df['gran_2_1'] = df['m_2_1']/df['m_do_promiv'] * 100
        df['gran_1_0_5'] = df['m_1_0_5']/df['m_do_promiv'] * 100
        df['gran_0_5_0_25'] = df['m_0_5_0_25']/df['m_do_promiv'] * 100
        df['gran_0_25_0_10'] = df['m_0_25_0_10']/df['m_do_promiv'] * 100
        df['gran_0_10_0_05'] = df['m_0_10_0_05']/df['m_do_promiv'] * 100
        df['gran_0_05_0_01'] = (df['m_do_promiv']-df['m_posle_promiv'])/df['m_do_promiv'] * 100
        df['gran_0_01_0_002'] = 0
        df['gran_0_002'] = 0

        df[config.COLUMNS_GRAN] = df[config.COLUMNS_GRAN].round(1)

        df['sum100'] = df[config.COLUMNS_GRAN].sum(axis=1)

        df = df[config.COLUMNS_GRAN_BD_LAB_NOMER]

        return df