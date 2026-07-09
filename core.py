from pathlib import Path
from gransostav import RaschetGranov
import pandas as pd
import config
import re
import os
import datetime
from database import Database

GROUP_DIR = Path(r"Y:\2026\Группа физических и механических испытаний")

def zagr_file(path):
    df = pd.read_excel(path, skiprows=4, header=[0, 1, 2], na_values=["-", "26_", "27_"])

    df.columns = [process_multiheader_column(col) for col in df.columns]

    df = df.rename(columns=config.COlUMNS)
    df = df[config.COlUMNS.values()]

    return df

def zagr_file2(path):
    df = pd.read_excel(
        path,
        sheet_name="Сводная физ св-в",
        skiprows=8,
        header=[0, 1, 2, 3, 4],
        na_values="-"
    )

    df.columns = [process_multiheader_column(col) for col in df.columns]

    df = df.rename(columns=config.RENAME_COLUMNS_EXCEL_RAB)
    df = df[config.RENAME_COLUMNS_EXCEL_RAB.values()]
    #
    df = df.dropna(subset=['lab_nomer'])

    return df


def process_multiheader_column(col):
    if isinstance(col, tuple):
        clean_parts = []
        for part in col:
            if pd.isna(part):
                continue
            part_str = str(part)
            if part_str.startswith("Unnamed:"):
                continue
            if part_str.strip() and part_str != "nan":
                clean_parts.append(part_str.strip())
        return "_".join(clean_parts) if clean_parts else f"column_{hash(col) % 1000}"
    return str(col).strip()


def obrabotka_df_posle_zagr(df):
    # 1. Валидация на дубли исходных lab_nomer (до ffill)
    original_lab = df['lab_nomer']

    # Игнорируем NaN, смотрим только на реальные значения
    non_null_mask = original_lab.notna()
    duplicated_mask = original_lab[non_null_mask].duplicated(keep=False)

    if duplicated_mask.any():
        duplicates = sorted(
            original_lab[non_null_mask][duplicated_mask].unique().tolist()
        )
        raise ValueError(
            f"Найдены дублирующиеся лабораторные номера: {duplicates}"
        )

    df['lab_nomer'] = df['lab_nomer'].ffill(limit=1)

    df = df.dropna(subset=['lab_nomer'])

    validate_no_missing(df, config.COLUMNS_OBYAZAT1)

    df_agg = df.groupby('lab_nomer').agg({**config.agg_dict, **config.temp_agg})

    df_agg.columns = [process_multiheader_column(col) for col in df_agg.columns]
    df_agg = df_agg.reset_index()

    df_agg[config.COLS_GRAN] = df_agg[config.COLS_GRAN].fillna(0)

    df_agg = df_agg.dropna(subset=['nomer_predv_first'])

    return df_agg


def zagr_tarirovki(path):
    df_tarirovk = pd.read_excel(path)
    df_tarirovk = df_tarirovk.set_index('№')

    return df_tarirovk


def rashet_popravki_areometr(df_agg, df_tarirovk):
    df_agg['popravka_t1'] = df_agg.apply(get_value1, axis=1, ref_df=df_tarirovk, col_temp='zamer_temp_1_last')
    df_agg['popravka_t2'] = df_agg.apply(get_value1, axis=1, ref_df=df_tarirovk, col_temp='zamer_temp_2_last')
    df_agg['popravka_t3'] = df_agg.apply(get_value1, axis=1, ref_df=df_tarirovk, col_temp='zamer_temp_3_last')

    df_agg['zamer_1'] = df_agg['zamer_temp_1_first'] + df_agg['popravka_t1']
    df_agg['zamer_2'] = df_agg['zamer_temp_2_first'] + df_agg['popravka_t2']
    df_agg['zamer_3'] = df_agg['zamer_temp_3_first'] + df_agg['popravka_t3']

    return df_agg


def get_value1(row, ref_df, col_temp):
    idx = row['areometr_first']
    col = row[col_temp]


    if idx not in ref_df.index:
        raise KeyError(f"Для пробы {row['lab_nomer']} ареометр {idx} отсутствует в тарировке!")

    if col not in ref_df.columns:
        raise KeyError(f"Для пробы {row['lab_nomer']} температура {col} отсутствует в тарировках!")

    # .at работает быстро для одиночного доступа по метке
    return ref_df.at[idx, col]


def rashet_x1_x2_x3(df_agg, udelka):
    df_agg['udelka'] = udelka

    df_agg['koef_K'] = (df_agg['gran_10_first'] + df_agg['gran_5_10_first'] + df_agg['gran_5_2_first'] + df_agg[
        'gran_2_1_first'])

    # df_agg = df_agg.dropna(subset=['zamer_temp_3_first']).copy()

    df_agg['X1'] = df_agg['udelka'] * df_agg['zamer_1'] / (df_agg['udelka'] - 1) / df_agg[
        'kolba_naveska_last'] * (100 - df_agg['koef_K'])
    df_agg['X2'] = df_agg['udelka'] * df_agg['zamer_2'] / (df_agg['udelka'] - 1) / df_agg[
        'kolba_naveska_last'] * (100 - df_agg['koef_K'])
    df_agg['X3'] = df_agg['udelka'] * df_agg['zamer_3'] / (df_agg['udelka'] - 1) / df_agg[
        'kolba_naveska_last'] * (100 - df_agg['koef_K'])

    return df_agg


def itog_raschet_gran(df_agg):
    df_agg['m_probi_bez_krupn'] = df_agg['kolba_naveska_last'] - df_agg[config.COLS_GRAN_KOEF_K].sum(axis=1)

    df_agg['gran_10_%'] = df_agg['gran_10_first'] / df_agg['kolba_naveska_last'] * 100
    df_agg['gran_5_10_%'] = df_agg['gran_5_10_first'] / df_agg['kolba_naveska_last'] * 100
    df_agg['gran_5_2_%'] = df_agg['gran_5_2_first'] / df_agg['kolba_naveska_last'] * 100
    df_agg['gran_2_1_%'] = df_agg['gran_2_1_first'] / df_agg['kolba_naveska_last'] * 100

    df_agg['gran_1_0_5_%'] = df_agg['gran_1_0_5_first'] / df_agg['m_probi_bez_krupn'] * (100 - df_agg['koef_K'])
    df_agg['gran_0_5_0_25_%'] = df_agg['gran_0_5_0_25_first'] / df_agg['m_probi_bez_krupn'] * (100 - df_agg['koef_K'])
    df_agg['gran_0_25_0_10_%'] = df_agg['gran_0_25_0_10_first'] / df_agg['m_probi_bez_krupn'] * (100 - df_agg['koef_K'])

    df_agg['gran_0.05-0.01_%'] = df_agg['X1'] - df_agg['X2']
    df_agg['gran_0.01-0.002_%'] = df_agg['X2'] - df_agg['X3']
    df_agg['gran_0.002_%'] = df_agg['X3']

    df_agg[config.cols_kr_prozent] = df_agg[config.cols_kr_prozent].round(1)
    df_agg[config.cols_melk_prozent] = df_agg[config.cols_melk_prozent].round(1)

    df_agg['gran_0,10-0,05_%'] = (100 - df_agg[config.cols_kr_prozent].sum(axis=1) - df_agg[
        config.cols_melk_prozent].sum(axis=1)).round(1)

    return df_agg


def rashet_gran(df_agg, df_tarirovk, udelka):
    df_agg = rashet_popravki_areometr(df_agg, df_tarirovk)
    df_agg = rashet_x1_x2_x3(df_agg, udelka)
    df_agg = itog_raschet_gran(df_agg)

    df_itog = df_agg[config.cols_prozent_vse].copy()
    spisok_otricat_grani = proverka_grana(df_itog)

    return df_itog, spisok_otricat_grani


def proverka_grana(df_itog):
    mask = (df_itog[config.cols_prozent]<0).any(axis=1)
    spisok_otricat_grani = list(df_itog.loc[mask, 'lab_nomer'])

    return spisok_otricat_grani


def validate_no_missing(df: pd.DataFrame, cols: list[str]) -> None:
    if df[cols].isna().any().any():
        
        rows_with_na = df[df[cols].isna().any(axis=1)]

        spisok_lab = list(rows_with_na['lab_nomer'])

        raise ValueError(
            f"В столбцах {cols} обнаружены пропуски.\n"
            f"Пробы с проблемами {spisok_lab}\n"
            f"Количество строк с пропусками: {len(rows_with_na)}")

def vigruzka_namiv(df_agg):
    df1 = df_agg[config.cols_1_stroka].rename(columns=config.columns_vigruzka_namiv1)
    df1['index'] = 1
    df2 = df_agg[config.cols_2_stroka].rename(columns=config.columns_vigruzka_namiv2)
    df2['index'] = 2

    result = pd.concat([df1, df2])
    result = result.sort_values(by=["lab_nomer", "index"])

    return result



def add_rab_svodn(pathes_ab_svodn: list):

    for path_rab_svodn in pathes_ab_svodn:
        try:
            df = zagr_file2(path_rab_svodn)

            item = self.list_widget2.currentItem()
            if item:
                db_id = item.data(Qt.UserRole)
                print(f"Данные из UserRole: {db_id}")
            else:
                print("Ничего не выбрано")

            self.orkestr_db.db_add.add_rab_svodnaya(df, db_id)

            df2 = RaschetGranov.zagr_excel(path_rab_svodn)
            df2 = RaschetGranov.raschet_gran_pesk(df2)

            self.orkestr_db.db_add.add_gran_bd(df2)
        except Exception as e:
            print(e)
            traceback.print_exc()

def sync_rab_svod():
    conn = Database.get_connection()
    cur = conn.cursor()
    cur.execute(

    )
