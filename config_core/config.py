RENAME_COLUMNS_EXCEL = {
    'Регистационный номер пробы': 'lab_nomer',
    'Масса навески до промывки g1a, г': 'm_do_promiv',
    'Масса навески после промывки g2a, г': 'm_posle_promiv',
    'Масса и процентное содержание  фракций_>10_Масса, г_%': 'm_10',
    'Масса и процентное содержание  фракций_10-5': 'm_10_5',
    'Масса и процентное содержание  фракций_5-2': 'm_5_2',
    'Масса и процентное содержание  фракций_2-1': 'm_2_1',
    'Масса и процентное содержание  фракций_1-0,5': 'm_1_0_5',
    'Масса и процентное содержание  фракций_0,5-0,25': 'm_0_5_0_25',
    'Масса и процентное содержание  фракций_0,25-0,10': 'm_0_25_0_10',
    'Масса и процентное содержание  фракций_0,10-0,05': 'm_0_10_0_05'
}

RENAME_COLUMNS_EXCEL_RAB = {
    'Регистрационный\n№ пробы_2': 'lab_nomer',
    'Уколы/Окатанность_6': 'ukol',
    'Наименование грунта \nпо ГОСТ 25100-2020_7': 'opisanie_razbor',
    'Природная влажность, д.е._19': 'wlashn',
    'Плотность\nг/см3_влажного\nгрунта, р_24': 'plotn',
    'Плотность частиц грунта\nр s, г/см3_26': 'udelka',
    'Содержание органического вещества, %_36': 'organika'
}

COLUMNS_GRAN = [
    'gran_10',
    'gran_5_10',
    'gran_5_2',
    'gran_2_1',
    'gran_1_0_5',
    'gran_0_5_0_25',
    'gran_0_25_0_10',
    'gran_0_10_0_05',
    'gran_0_05_0_01',
    'gran_0_01_0_002',
    'gran_0_002'
]

COLUMNS_GRAN_BD_LAB_NOMER = [
    'lab_nomer',
    *COLUMNS_GRAN,
]


COLUMNS_GRAN_BD = [
    'proba_id',
    *COLUMNS_GRAN,
]

cols_bd_rename = {
    'gran_10_%': "gran_10",
    'gran_5_10_%': "gran_5_10",
    'gran_5_2_%': "gran_5_2",
    'gran_2_1_%': "gran_2_1",
    'gran_1_0_5_%': "gran_1_0_5",
    'gran_0_5_0_25_%': "gran_0_5_0_25",
    'gran_0_25_0_10_%': "gran_0_25_0_10",
    'gran_0,10-0,05_%': "gran_0_10_0_05",
    'gran_0.05-0.01_%': "gran_0_05_0_01",
    'gran_0.01-0.002_%': "gran_0_01_0_002",
    'gran_0.002_%': "gran_0_002"
}

COlUMNS = {
    'Вписать номер без преффикса': "nomer_predv",
    'Регистационный номер пробы': "lab_nomer",
    'Номер колбы_Масса возд. сух. навески, г': 'kolba_naveska_s_rast',
    'Номер колбы_Масса возд. сух. навески, г с учетом РО': "kolba_naveska",
    'Номер ареометра': 'areometr',
    '1 замер_Температура, °С': 'zamer_temp_1',
    '2 замер_Температура, °С': 'zamer_temp_2',
    '3 замер_Температура, °С': 'zamer_temp_3',
    'Содержание растительных остатков': 'rast_ost',
    'Масса фракций, г_>10': 'gran_10',
    'Масса фракций, г_5-10': 'gran_5_10',
    'Масса фракций, г_5-2': 'gran_5_2',
    'Масса фракций, г_2-1': 'gran_2_1',
    'Масса фракций, г_1-0,5': 'gran_1_0_5',
    'Масса фракций, г_0,5-0,25': 'gran_0_5_0_25',
    'Масса фракций, г_0,25-0,10': 'gran_0_25_0_10',
}

COLUMNS_OBYAZAT1 = [
    "lab_nomer",
    "kolba_naveska",
    'zamer_temp_1',
    'zamer_temp_2',
    'zamer_temp_3',
]

COLS_GRAN_KOEF_K = [
    'gran_10_first',
    'gran_5_10_first',
    'gran_5_2_first',
    'gran_2_1_first',
]

COLS_GRAN = [
    *COLS_GRAN_KOEF_K,
    'gran_1_0_5_first',
    'gran_0_5_0_25_first',
    'gran_0_25_0_10_first'
]

agg_dict = {
    'nomer_predv': 'first',
    'kolba_naveska_s_rast': 'last',
    'areometr': 'first',
    'rast_ost': 'first',
    'gran_10': 'first',
    'gran_5_10': 'first',
    'gran_5_2': 'first',
    'gran_2_1': 'first',
    'gran_1_0_5': 'first',
    'gran_0_5_0_25': 'first',
    'gran_0_25_0_10': 'first',
}

temp_agg = {
    'kolba_naveska': ['first', 'last'],
    'zamer_temp_1': ['first', 'last'],
    'zamer_temp_2': ['first', 'last'],
    'zamer_temp_3': ['first', 'last'],
}

cols_kr_prozent = [
    'gran_10_%',
    'gran_5_10_%',
    'gran_5_2_%',
    'gran_2_1_%',
    'gran_1_0_5_%',
    'gran_0_5_0_25_%',
    'gran_0_25_0_10_%'
]

cols_melk_prozent = [
    'gran_0.05-0.01_%',
    'gran_0.01-0.002_%',
    'gran_0.002_%'
]

cols_prozent = [
    *cols_kr_prozent,
    'gran_0,10-0,05_%',
    *cols_melk_prozent
]

cols_prozent_vse = [
    'lab_nomer',
    *cols_prozent,
]

RENAME_COLUMNS_EXCEL_RAB = {
    'Регистрационный\n№ пробы_2': 'lab_nomer',
    'Уколы/Окатанность_6': 'ukol',
    'Наименование грунта \nпо ГОСТ 25100-2020_7': 'opisanie_razbor',
    'Природная влажность, д.е._19': 'wlashn',
    'Плотность\nг/см3_влажного\nгрунта, р_24': 'plotn',
    'Плотность частиц грунта\nр s, г/см3_26': 'udelka',
    'Содержание органического вещества, %_36': 'organika'
}

cols_bd_rashet = [
    "lab_nomer",
    'kolba_naveska_first',
    'kolba_naveska_last',
    'areometr_first',
    'zamer_temp_1_first',
    'zamer_temp_1_last',
    'zamer_temp_2_first',
    'zamer_temp_2_last',
    'zamer_temp_3_first',
    'zamer_temp_3_last',
    'gran_10_first',
    'gran_5_10_first',
    'gran_5_2_first',
    'gran_2_1_first',
    'gran_1_0_5_first',
    'gran_0_5_0_25_first',
    'gran_0_25_0_10_first'
]


cols_1_stroka = [
    "lab_nomer",
    'kolba_naveska_first',
    'areometr_first',
    'zamer_temp_1_first',
    'zamer_temp_2_first',
    'zamer_temp_3_first',
    'gran_10_first',
    'gran_5_10_first',
    'gran_5_2_first',
    'gran_2_1_first',
    'gran_1_0_5_first',
    'gran_0_5_0_25_first',
    'gran_0_25_0_10_first'
]

cols_2_stroka = [
    "lab_nomer",
    'kolba_naveska_last',
    'zamer_temp_1_last',
    'zamer_temp_2_last',
    'zamer_temp_3_last',
]

columns_vigruzka_namiv1 = {
    "kolba_naveska_first": "kolba_naveska",
    "zamer_temp_1_first": "zamer_temp_1",
    "zamer_temp_2_first": "zamer_temp_2",
    "zamer_temp_3_first": "zamer_temp_3",
}

columns_vigruzka_namiv2={
    "kolba_naveska_last": "kolba_naveska",
    "zamer_temp_1_last": "zamer_temp_1",
    "zamer_temp_2_last": "zamer_temp_2",
    "zamer_temp_3_last": "zamer_temp_3",
}

