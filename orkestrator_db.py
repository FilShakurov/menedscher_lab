import pandas as pd
from database import Database


class ZagrVDatabase:
    def __init__(self, db):

        self.db = db

    def add_object_bd(self, name_object, year=None, name_ilya=None):
        self.db.add_object(name_object, year=year, name_ilya=name_ilya)

    def add_partiya_bd(self, name_partii, id_object):
        partiya_id = self.db.add_partiya(name_partii, id_object)

        return partiya_id

    def add_gran_bd(self, df):
        # df = pd.read_excel(path)
        self.db.save_grans_bulk_by_lab_nomer(df)

    def add_gran_rashet_bd(self, df_rashet):
        # df = pd.read_excel(path)
        self.db.save_grans_raschet_bulk_by_lab_nomer(df_rashet)

    def add_rab_svodnaya(self, df, id_partii):
        self.db.add_probi(df, id_partii)
        self.db.save_fizika_bulk_by_lab_nomer(df)



class DeleteIzDatabase:
    def __init__(self, db):
        self.db = db

    def del_object_bd(self, object_id):
        self.db.delete_object(self, object_id)

    def del_partiya_bd(self, id_partii):
        self.db.delete_partiya(id_partii)

class ShowIzDatabase:
    def __init__(self, db):
        self.db = db

    def show_grani_part_bd(self, partiya_id):
        df = self.db.get_gran_data_by_party_id(partiya_id)

        return df

    def poln_info_part(self, partiya_id):
        df = self.db.get_poln_info_data_by_party_id(partiya_id)

        return df

    def show_all_objects(self):
        rows = self.db.show_all_objects()
        return rows

    def show_all_partii_object(self, object_id):
        rows = self.db.show_all_partii_by_object(object_id)
        return rows

    def get_namivs(self, partiya_id):
        df = self.db.get_rashet_gran_part_by_id(partiya_id)

        return df



class MainCore:
    def __init__(self, db_file):
        self.db = Database(db_file)
        self.db_delete = DeleteIzDatabase(self.db)
        self.db_add = ZagrVDatabase(self.db)
        self.db_show = ShowIzDatabase(self.db)


# config_core = MainCore("database.db")
#
# config_core.db_add.add_object_bd("ВСЖМ-123")
# #
# config_core.db_add.add_partiya_bd("1 Партия", 2)
#
# config_core.db_add.add_probi_bd("Пробы.xlsx", 3)

# config_core.db_add.add_gran_bd("Граны2.xlsx")
#
# config_core.db_show.show_grani_part_bd(1)
# config_core.db_show.show_grani_part_bd(2)
#
# config_core.db_show.show_poln_info_part_bd(1)






# db.add_object('КАД-2')
#
# rows = db.show_all_objects()
# for row in rows:
#     print(row["id"], row["name_object"], row["created_at"])

# print(db.name_object_by_id(1)['name_object'])
# print(db.id_object_by_name("КАД-2")['id'])
# print(db.date_object_by_name("КАД-2")['created_at'])

# db.add_partiya('1-1', 1)
# db.add_partiya('1-2', 1)
# db.add_partiya('1-3', 1)
# db.add_partiya('2', 1)


# rows = db.show_all_partii_by_object(1)
#
# if len(rows) == 0:
#     print("Партий неет")
#
# for row in rows:
#     print(row["id"], row["name_partii"], row["created_at"])

# df = pd.DataFrame({
#     'lab_nomer': ['25_00001', '25_00003', '25_00004'],
# })
# #
# db.add_probi(df, 1)

# df = pd.DataFrame({
#     'lab_nomer': ['25_00001', '25_00003', '25_00004'],
#     'gr10': ['0.33', '2', '3'],
#     'gr5': ['0.75', '2', '3'],
#     'gr2': ['0.44', '2', '3'],
#     'gr1': ['33', '2', '3'],
#     'gr05': ['0.99', '2', '3'],
#     'gr025': ['17', '2', '3'],
#     'gr01': ['99', '2', '3'],
# })
#
# db.save_grans_bulk_by_lab_nomer(df)

# db.add_partiya('3', 1)

# db.delete_partiya(1)

# db.delete_object(1)

# df = db.get_gran_data_by_party_id(1)
#
# if len(df) == 0:
#     print("Партий неет")
#
# print(df)
