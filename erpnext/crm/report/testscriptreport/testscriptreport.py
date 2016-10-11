# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def get_chart_data():
	x_intervals = ['x']
	
	asset_data, liability_data, equity_data = [], [], []
	
	for p in range(0, 2):
		if asset:
			asset_data.append(p)
		if liability:
			liability_data.append(p*2)
		if equity:
			equity_data.append(p*p)
		
	columns = [x_intervals]
	if asset_data:
		columns.append(["Data 1"] + asset_data)
	if liability_data:
		columns.append(["Data 2"] + liability_data)
	if equity_data:
		columns.append(["Data 3"] + equity_data)

	return {
		"data": {
			'columns': [["Data1", 1,2,3],["Data 2", 2,3,4]]
		},
		chart_type: 'line',
	}

def execute(filters=None):
	columns, data, message, chart = [], [], [], []
	return columns, data, "Whats this", get_chart_data()

