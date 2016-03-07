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
	result = frappe.db.sql("""select so.customer,
								so.name, 
								so.transaction_date,
								so.new_order_type,
								so.budget,
								soi.qty, 
								soi.delivered_qty, 
								soi.qty-soi.delivered_qty,
								soi.assigned_qty,
								soi.item_code, 
								soi.item_name, 
								soi.item_group,
								soi.base_rate,
								((soi.qty-soi.delivered_qty) * soi.base_rate) as extended_rate,
								soi.stop_status,
								soi.stopped_status,
								soi.date_stopped
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
			conditions.append("%s.%s = '%s'"%("soi" if key in ['item_code', 'qty', 'delivered_qty', 'item_group', 'stop_status', 'stopped_status', 'date_stopped'] else "so", key, filters.get(key)))


	return " and {}".format(" and ".join(conditions)) if conditions else ""


def get_columns():
	return [
			# _("Picked") + ":Check:100",
			_("Customer") + ":Link/Customer:150",
			_("Sales Order") + ":Link/Sales Order:120",
			_("Date") + ":Date:",
			_("Order Type") + ":Data:110",
			_("Budget") + ":Link/Budget:110",
			_("Qty") + ":Float:80",
			_("Delivered Qty") + ":Int:80",
			_("Qty to Deliver") + ":Int:80",
			_("Assigned Qty") + ":Int:80",
			_("Item Code") + ":Link/Item:110",
			_("Item Name") + ":Data:110",
			_("Item Group") + ":Data:110",
			_("Rate(AUD)") + ":Currency:100",
			_("Extended Rate") + ":Currency:100",
			_("Stopped") + ":Data:100",
			_("Stopped Status") + ":Data:100",
			_("Date Stopped") + ":Data:100",
	]