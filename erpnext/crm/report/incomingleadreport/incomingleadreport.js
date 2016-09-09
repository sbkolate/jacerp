// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["IncomingLeadReport"] = {
	"filters": [
		{
			"fieldname":"contact_by",
			"label": "Assigned Salesman",
			"fieldtype": "Link",
			"options": "Sales Partner",
			"reqd": 0
		},
	]
}
