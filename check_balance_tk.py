import json
import re
import datetime
import pickle
import traceback
from fast_bitrix24 import Bitrix

LIMIT = 5000.00
TASK_TITLE = {1: 'Пополнить счет Premium Card', 2: 'Пополнить счет e100'}
AUDITOR_ID = 13574
RESPONSIBLE_DEP_ID = 42
CREATOR_DEP_ID = 3
DEBUG_GROUP_ID = 1418
TYPE = {'PREMIUM': 1, 'E100': 2}
bx24 = Bitrix('your_webhook')


def __logging_and_debag(func):
	def wrapper(*data_func):
		date_start = datetime.datetime.now()
		args = data_func
		try:
			res = func(*data_func)
		except Exception as error:
			res = traceback.format_exc()
			send_for_debugging(*args, res)
		finally:
			date_end = datetime.datetime.now()
			time_work = date_end - date_start
			log_massage = 'Date start: {}\nDate end: {}\nTime in work: {}\nArgs: {}\nResult: {}\n\n'.format(
				date_start, date_end, time_work, args, res)
			with open('check_balance_tk.log', 'a') as f:
				f.write(log_massage)
		return res

	return wrapper


@__logging_and_debag
def check_balance(task_id, task_type):
	balance = None
	task = get_task_data(task_id)
	if task_type == TYPE['PREMIUM']:
		balance = find_balance_premium(task['description'])
	if task_type == TYPE['E100']:
		balance = find_balance_e100()
	if balance >= LIMIT:
		result = close_task(task_id)
	else:
		result = add_task(task_id, task_type, balance)
		close_task(task_id)
	return result


def get_task_data(task_id):
	task = bx24.get_all('tasks.task.get', {'taskId': task_id, 'select': ['ID', 'TITLE', 'DESCRIPTION']})['task']
	return task


def find_balance_premium(text):
	pattern = r'-?\d*\s\d*[.]\d*\s'
	balance = re.search(pattern, text)
	return float(balance[0].replace(' ', ''))


def find_balance_e100():
	with open('e100_balance.pickle', 'rb') as f:
		today_balance = pickle.load(f)
	if today_balance['date'] == datetime.date.today():
		return float(today_balance['balance'])
	raise ValueError('Incorrect balance date')


def close_task(task_id):
	return bx24.call('tasks.task.complete', {'taskId': task_id})


def add_task(task_id, task_type, balance):
	deps = get_users_id(RESPONSIBLE_DEP_ID, CREATOR_DEP_ID)
	params = {'fields': {'TITLE': TASK_TITLE[task_type],
						 'DESCRIPTION': f'Баланс лицевого счета составляет {balance} руб.',
						 'DEADLINE': datetime.datetime.now() + datetime.timedelta(days=1),
						 'PRIORITY': 2,
						 'CREATED_BY': deps['create_dep']['create_leader'],
						 'RESPONSIBLE_ID': deps['resp_dep']['resp_leader'],
						 'ACCOMPLICES': deps['resp_dep']['resp_emploees'],
						 'AUDITORS': [AUDITOR_ID],
						 'PARENT_ID': task_id
						 }
			  }
	return bx24.call('tasks.task.add', params)


def get_users_id(resp_dep_id, creat_dep_id):
	resp_dep = bx24.get_all('department.get', {'ID': resp_dep_id})[0]
	resp_dep_leader_id = resp_dep['UF_HEAD']
	resp_dep_emploees_id = [emploee['ID'] for emploee in
							bx24.call('user.get', {'FILTER': {'ACTIVE': 'Y', 'UF_DEPARTMENT': resp_dep['ID']}})
							if emploee['ID'] != resp_dep_leader_id
							]
	creat_dep = bx24.get_all('department.get', {'ID': creat_dep_id})[0]
	creat_dep_leader_id = creat_dep['UF_HEAD']
	deps = {'resp_dep': {'resp_leader': resp_dep_leader_id, 'resp_emploees': resp_dep_emploees_id},
			'create_dep': {'create_leader': creat_dep_leader_id}
			}
	return deps


def send_for_debugging(task_id, task_type, error):
	debugger = bx24.get_all('sonet_group.user.get', {'ID': DEBUG_GROUP_ID})[0]['USER_ID']
	params = {'fields': {'TITLE': 'Ошибка обработки задачи "{}"'.format(TASK_TITLE[task_type]),
						 'DESCRIPTION': error,
						 'DEADLINE': datetime.datetime.now() + datetime.timedelta(days=1),
						 'PRIORITY': 2,
						 'CREATED_BY': debugger,
						 'RESPONSIBLE_ID': debugger,
						 'AUDITORS': [AUDITOR_ID],
						 'GROUP_ID': DEBUG_GROUP_ID,
						 'PARENT_ID': task_id
						 }
			  }

	return bx24.call('tasks.task.add', params)
