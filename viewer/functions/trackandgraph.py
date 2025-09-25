import sqlite3, datetime, pytz
from viewer.functions.utils import unixtime_to_datetime

def read_trackandgraph_file(path, date_from=None, date_to=None):

	try:
		db = sqlite3.connect(path)
		cur = db.cursor()
	except:
		return []

	dts = date_from
	dte = date_to
	if dts is None:
		dts = pytz.utc.localize(datetime.datetime(1970, 1, 1, 0, 0, 0))
	if dte is None:
		dte = pytz.utc.localize(datetime.datetime.utcnow())
	query = "select groups_table.name as group_name, features_table.name as feature_name, feature_description, epoch_milli, data_points_table.value from groups_table, features_table, data_points_table where group_id = groups_table.id and feature_id = features_table.id order by group_name, feature_name, epoch_milli ;"
	data = {}
	for row in list(cur.execute(query)):
		dt = unixtime_to_datetime(row[3] / 1000)
		if dt < dts:
			continue
		if dt > dte:
			continue
		k = row[0] + '/' + row[1]
		if not k in data:
			data[k] = {"category": row[0], "label": row[1], "description": row[2], "total": 0.0, "latest": None, "values": []}
		value = float(row[4])
		if data[k]['latest'] is None:
			data[k]['latest'] = dt
		if dt > data[k]['latest']:
			data[k]['latest'] = dt
		data[k]['total'] = data[k]['total'] + value
		data[k]['values'].append([dt, value])
	return list(data.values())
