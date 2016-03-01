// Copyright (c) 2013, digitales and contributors
// For license information, please see license.txt

frappe.query_reports["Delivery Note Back Order Report"] = {
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
			"fieldname":"qty_to_deliver",
			"label": __("Qty to Deliver"),
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
	]
}
