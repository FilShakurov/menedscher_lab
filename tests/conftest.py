import sys
import pytest
import pandas as pd
from config_core.core import zagr_file, zagr_tarirovki

@pytest.fixture
def zagr_df_excel():
    path_namiv = 'excelki/test_namiv2.xlsx'
    path_tarirovki = "excelki/tarirovki.xlsx"

    df = zagr_file(path_namiv)
    df_tarirovk = zagr_tarirovki(path_tarirovki)
    udelka = 2.7
    return {
        'df': df,
        'df_tarirovk': df_tarirovk,
        'udelka': udelka,
    }

