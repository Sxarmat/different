import pandas as pd
from fast_bitrix24 import Bitrix

BX24 = Bitrix('your_webhook')

DATA_IN = 'Сотрудники.xlsx'


def check_employees_in_BX24(file):
    frame = get_frame(file)
    analyzed_frame = analysis_frame(frame)
    return analyzed_frame


def get_frame(file):
    data = pd.read_excel(io=file,
                         engine='openpyxl',
                         header=4,
                         sheet_name=['list1', 'list2', 'list3', 'list4', 'list5']
                         )
    frame = pd.concat(data).reset_index(drop=True)
    frame = frame.assign(ID_Bitrix=None)
    return frame


def analysis_frame(frame):
    for idx in range(len(frame.index)):
        cell = frame.iloc[idx]['Сотрудник']
        if pd.isna(cell):
            continue
        full_name = get_full_name(cell)
        frame['ID_Bitrix'][idx] = find_user(full_name)
    return frame


def get_full_name(_str):
    return _str.split()[:3]


def find_user(lst):
    filter = {'LAST_NAME': lst[0],
              'NAME': lst[1],
              'SECOND_NAME': lst[2]
              }
    user = BX24.call('user.get', {'FILTER': filter})
    if user:
        return user[0]['ID']
    return 'Не зарегистрирован'


if __name__ == '__main__':
    data_out = check_employees_in_BX24(DATA_IN)
    data_out.to_excel('table_result.xlsx')
