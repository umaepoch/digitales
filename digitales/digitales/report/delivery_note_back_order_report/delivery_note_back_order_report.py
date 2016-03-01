# Copyright (c) 2013, digitales and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_data(filters):
	result = frappe.db.sql("""select so.name,
								so.customer, 
								so.transaction_date, 
								soi.item_code, 
								soi.qty, 
								soi.delivered_qty, 
								soi.qty-soi.delivered_qty,
								((soi.qty-soi.delivered_qty) * soi.rate),
								so.net_total_export, 
								so.delivery_date, 
								soi.item_name, 
								soi.item_group,
								so.budget,
								so.new_order_type 
							from 
								`tabSales Order`so,
								`tabSales Order Item`soi 
							where 
								so.name = soi.parent and 
								so.docstatus = 1 and
								(soi.qty-soi.delivered_qty) != 0 {0}
						""".format(get_conditions(filters)),as_list=1)
	return result

def get_conditions(filters):
	conditions = []
	for key in filters:
		if filters.get(key) and key == 'item_name':
			conditions.append("soi.item_name like '%%%s%%'"%filters.get(key))
		elif filters.get(key) and key == 'qty_to_deliver':
			conditions.append("(soi.qty-soi.delivered_qty)= %s"%filters.get(key))
		elif filters.get(key) and key != 'qty_to_deliver':
			conditions.append("%s.%s = '%s'"%("soi" if key in ['item_code', 'qty', 'delivered_qty', 'item_group'] else "so", key, filters.get(key)))


	return " and {}".format(" and ".join(conditions)) if conditions else ""


def get_columns():
	return [
			# _("Picked") + ":Check:100",
			_("Sales Order") + ":Link/Sales Order:120",
			_("Customer") + ":Link/Customer:150",
			_("Date") + ":Date:",
			_("Item Code") + ":Link/Item:110",
			_("Qty") + ":Float:80",
			_("Delivered Qty") + ":Int:100",
			_("Qty to Deliver") + ":Int:100",
			_("Amount") + ":Data:100",
			_("Total") + ":Float:120",
			_("Expected Delivery Date") + ":Date:120",
			_("Item Name") + ":Data:110",
			_("Item Group") + ":Data:110",
			_("Budget") + ":Link/Budget:110",
			_("Order Type") + ":Data:110"
		]