import os
import sys
from joblib import load
import pandas as pd
import numpy as np
import re
import config
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression


class ClassPredict:
    @staticmethod
    def predict(df_table):
        ukol_rf_path = os.path.join(app_dir(), "models/ukol_rf.joblib")
        wlashn_lr_path = os.path.join(app_dir(), "models/wlashn_lr.joblib")
        plotn_lr_path = os.path.join(app_dir(), "models/plotn_lr.joblib")

        load_ukol_rf = load(ukol_rf_path)
        load_wlashn_lr = load(wlashn_lr_path)
        load_plotn_lr = load(plotn_lr_path)

        cols_model = ['lab_nomer', 'ukol_values', 'wlashn', 'plotn', 'gran_do_0,002', 'neodnorodn']
        cols_ukol = ['wlashn', 'plotn', 'gran_do_0,002', 'neodnorodn']
        cols_wlashn = ['plotn', 'ukol_values', 'gran_do_0,002', 'neodnorodn']
        cols_plotn = ['wlashn', 'ukol_values', 'gran_do_0,002', 'neodnorodn']



        df = obrabotka_df(df_table)

        df = df.rename(columns={'gran_0_002': 'gran_do_0,002',
                                'ukol': 'ukol_values'})

        df = df[cols_model].copy()

        Xtest = df[cols_ukol].copy()

        df['ukol_predict'] = load_ukol_rf.predict(Xtest)

        Xtest = df[cols_wlashn].copy()
        df['wlashn_predict'] = load_wlashn_lr.predict(Xtest)

        Xtest = df[cols_plotn].copy()
        df['plotn_predict'] = load_plotn_lr.predict(Xtest)

        df['ukol_predict'] = df['ukol_predict'].round(1)
        df['wlashn_predict'] = df['wlashn_predict'].round(3)
        df['plotn_predict'] = df['plotn_predict'].round(2)

        bad_rows_plotn = plotn_bad_rows(df)

        bad_rows_wlashn = wlashn_bad_rows(df)

        bad_rows_ukol = ukol_bad_rows(df)

        print(bad_rows_plotn.columns)
        print(bad_rows_wlashn.columns)
        print(bad_rows_ukol.columns)

        print(bad_rows_plotn.columns.is_unique)
        print(bad_rows_wlashn.columns.is_unique)
        print(bad_rows_ukol.columns.is_unique)

        bad_rows_plotn = bad_rows_plotn.reset_index(drop=True)
        bad_rows_wlashn = bad_rows_wlashn.reset_index(drop=True)
        bad_rows_ukol = bad_rows_ukol.reset_index(drop=True)

        bad_rows = pd.concat([bad_rows_plotn, bad_rows_wlashn], axis=0, ignore_index=True)

        bad_rows = pd.concat([bad_rows, bad_rows_ukol], axis=0, ignore_index=True)

        return bad_rows

def obrabotka_df(df):
    df['neodnorodn'] = df[config.cols_bd_rename.values()].pow(2).sum(axis=1)

    df['ukol'] = df['ukol'].apply(row_mean_from_str)
    df['ukol'] = df['ukol'].round(1)
    df = df.dropna()

    return df

def plotn_bad_rows(df):
    threshold = 0.05
    df['plotn_diff'] = (df['plotn'] - df['plotn_predict']).abs()
    bad_rows = df[df['plotn_diff'] > threshold]

    if not bad_rows.empty:
        bad_rows['error_type'] = 'плотность'
    return bad_rows


def wlashn_bad_rows(df):
    threshold = 0.035
    df['wlashn_diff'] = (df['wlashn'] - df['wlashn_predict']).abs()
    bad_rows = df[df['wlashn_diff'] > threshold]

    if not bad_rows.empty:
        bad_rows['error_type'] = 'влажность'
    return bad_rows

def ukol_bad_rows(df):
    threshold = 4
    df['ukol_diff'] = (df['ukol_values'] - df['ukol_predict']).abs()
    bad_rows = df[df['ukol_diff'] > threshold]

    if not bad_rows.empty:
        bad_rows['error_type'] = 'Укол'
    return bad_rows

def parse_numbers(s):
    if pd.isna(s):
        return []
    # приводим к строке
    s = str(s).strip()
    if not s:
        return []

    # убираем скобки
    s = s.replace('(', '').replace(')', '')

    # заменим ; и , на пробел, последовательности пробелов схлопнутся split'ом
    s = s.replace(';', ' ').replace(',', ' ')

    # можно дополнительно нормализовать любые подряд идущие пробелы (не обязательно)
    s = re.sub(r'\s+', ' ', s)

    nums = []
    for token in s.split(' '):
        if not token:
            continue
        try:
            # если только 0/1, можно оставить int; иначе float
            val = float(token)
            nums.append(val)
        except ValueError:
            # игнорируем мусор/текст
            continue
    return nums

def row_mean_from_str(s):
    nums = parse_numbers(s)
    if not nums:
        return np.nan
    return np.mean(nums)

def app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))
