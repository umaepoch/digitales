// Copyright (c) 2013, digitales and contributors
// For license information, please see license.txt

frappe.query_reports["Item Back Order Report"] = {
	"filters": [
		{
			"fieldname":"item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname":"item_name",
			"label": __("Item Name"),
			"fieldtype": "Data"
		},
		{
			"fieldname":"new_order_type",
			"label": __("Order Type"),
			"fieldtype": "Select",
			"options": ["","Standard Order","Standing Request","Reader Request"]
		},
		{
			"fieldname":"budget",
			"label": __("Budget"),
			"fieldtype": "Link",
			"options":"Budget"
		},
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options":"Customer"
		},
		{
			"fieldname":"name",
			"label": __("Sales Order"),
			"fieldtype": "Link",
			"options":"Sales Order"
		},
		{
			"fieldname":"transaction_date",
			"label": __("Date"),
			"fieldtype": "Date"
		},
		{
			"fieldname":"stop_status",
			"label": __("Stopped"),
			"fieldtype": "Select",
			"options": ["", "Yes", "No"]
		},
		{
			"fieldname":"status",
			"label": __("Status"),
			"fieldtype": "Select",
			"default": "Submitted",
			"options": ["Draft", "Submitted", "Stopped", "Cancelled"]
		},
	]
}
