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
    'gran_5-10_%': "gran_5_10",
    'gran_5-2_%': "gran_5_2",
    'gran_2-1_%': "gran_2_1",
    'gran_1-0,5_%': "gran_1_0_5",
    'gran_0,5-0,25_%': "gran_0_5_0_25",
    'gran_0,25-0,10_%': "gran_0_25_0_10",
    'gran_0,10-0,05_%': "gran_0_10_0_05",
    'gran_0.05-0.01_%': "gran_0_05_0_01",
    'gran_0.01-0.002_%': "gran_0_01_0_002",
    'gran_0.002_%': "gran_0_002"
}

COlUMNS = {
    'Вписать номер без преффикса': "nomer_predv",
    'Регистационный номер пробы': "lab_nomer",
    'Номер колбы_Масса возд. сух. навески, г': 'kolba/naveska_s_rast',
    'Номер колбы_Масса возд. сух. навески, г с учетом РО': "kolba/naveska",
    'Номер ареометра': 'areometr',
    '1 замер_Температура, °С': '1_zamer/temp',
    '2 замер_Температура, °С': '2_zamer/temp',
    '3 замер_Температура, °С': '3_zamer/temp',
    'Содержание растительных остатков': 'rast_ost',
    'Масса фракций, г_>10': 'gran_10',
    'Масса фракций, г_5-10': 'gran_5-10',
    'Масса фракций, г_5-2': 'gran_5-2',
    'Масса фракций, г_2-1': 'gran_2-1',
    'Масса фракций, г_1-0,5': 'gran_1-0,5',
    'Масса фракций, г_0,5-0,25': 'gran_0,5-0,25',
    'Масса фракций, г_0,25-0,10': 'gran_0,25-0,10',
}

COLUMNS_OBYAZAT1 = [
    "lab_nomer",
    "kolba/naveska",
    '1_zamer/temp',
    '2_zamer/temp',
    '3_zamer/temp',
]

COLS_GRAN_KOEF_K = [
    'gran_10_first',
    'gran_5-10_first',
    'gran_5-2_first',
    'gran_2-1_first',
]

COLS_GRAN = [
    *COLS_GRAN_KOEF_K,
    'gran_1-0,5_first',
    'gran_0,5-0,25_first',
    'gran_0,25-0,10_first'
]

agg_dict = {
    'nomer_predv': 'first',
    'kolba/naveska_s_rast': 'last',
    'kolba/naveska': 'last',
    'areometr': 'first',
    'rast_ost': 'first',
    'gran_10': 'first',
    'gran_5-10': 'first',
    'gran_5-2': 'first',
    'gran_2-1': 'first',
    'gran_1-0,5': 'first',
    'gran_0,5-0,25': 'first',
    'gran_0,25-0,10': 'first',
}

temp_agg = {
    '1_zamer/temp': ['first', 'last'],
    '2_zamer/temp': ['first', 'last'],
    '3_zamer/temp': ['first', 'last'],
}

cols_kr_prozent = [
    'gran_10_%',
    'gran_5-10_%',
    'gran_5-2_%',
    'gran_2-1_%',
    'gran_1-0,5_%',
    'gran_0,5-0,25_%',
    'gran_0,25-0,10_%'
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

