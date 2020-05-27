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
	result = frappe.db.sql("""SELECT so.customer,
								so.po_no,
								so.name,
								so.shipping_address_name,
								so.transaction_date,
								soi.release_date_of_item,
								so.new_order_type,
								so.budget,
								soi.qty, 
								ifnull(soi.delivered_qty, 0),
								CASE
									WHEN soi.stop_status='No' THEN (soi.qty-ifnull(soi.delivered_qty, 0))
									ELSE 0
								END AS qty_to_deliver,
								soi.assigned_qty,
								soi.item_code, 
								soi.item_name, 
								soi.item_group,
								soi.line_item,
								soi.price_list_rate as rrp_aud,
								soi.base_rate,
								((soi.qty-ifnull(soi.delivered_qty,0)) * soi.base_rate) as extended_rate,
								((soi.qty-ifnull(soi.delivered_qty,0)) * soi.base_rate) * 1.1 as gross_amount,
								soi.stop_status,
								soi.stopped_status,
								soi.date_stopped,
								so.status,
								so.comment,
								soi.release_date_of_item,
                                                                soi.catalogued,
								soi.default_supplier,
                                                                soi.classification,
                                                                soi.poupular

							FROM 
								`tabSales Order`so,
								`tabSales Order Item`soi 
							WHERE 
								so.name = soi.parent and 
								(soi.qty-ifnull(soi.delivered_qty, 0)) != 0 {0}
						""".format(get_conditions(filters)),as_list=1)
	return result

def get_conditions(filters):
	conditions = []
	for key in filters:
		if filters.get(key) and key == 'item_name':
			conditions.append("soi.item_name like '%%%s%%'"%filters.get(key))
		elif filters.get(key) and key != 'qty_to_deliver':
			soi_keys = [
					'item_code',
					'qty',
					'delivered_qty',
					'item_group',
					'stop_status',
					'stopped_status',
					'date_stopped'
				]
			if key in soi_keys:
				cond = "soi.%s = '%s'"%(key, filters.get(key))
			else:
				if key == "status" and filters.get(key) == "Not Cancelled":
					cond = "so.%s <> '%s'"%(key, "Cancelled")
				else:
					cond = "so.%s =	'%s'"%(key, filters.get(key))

			conditions.append(cond)

	return " and {}".format(" and ".join(conditions)) if conditions else ""


def get_columns():
	return [
			# _("Picked") + ":Check:100",
			_("Customer") + ":Link/Customer:150",
			_("PO No") + ":Data:110",
			_("Sales Order") + ":Link/Sales Order:120",
			_("Shipping address") + ":Link/Address:120",
			_("Date") + ":Date:",
			_("Release Date Of Item") + ":Date:",
			_("Order Type") + ":Data:110",
			_("Budget") + ":Link/Budget:110",
			_("Qty") + ":Float:80",
			_("Delivered Qty") + ":Int:80",
			_("Qty to Deliver") + ":Int:80",
			_("Assigned Qty") + ":Int:80",
			_("Item Code") + ":Link/Item:110",
			_("Item Name") + ":Data:110",
			_("Item Group") + ":Data:110",
			_("Line Order Item") + ":Data:110",
			_("RRP(AUD)") + ":Currency:100",
			_("Rate(AUD)") + ":Currency:100",
			_("Extended Rate") + ":Currency:100",
			_("Gross Amount (AUD)") + ":Currency:100",
			_("Stopped") + ":Data:100",
			_("Stopped Status") + ":Data:100",
			_("Date Stopped") + ":Data:100",
			_("Status") + ":Data:100",
			_("Comments") + ":Data:100",
			_("Product Release Date") + ":Date:200",
                        _("Catalouged") + ":Data:100",
			_("Default Supplier") + ":Link/Supplier:150",
                        _("Classification") +  ":Data:100",
                        _("Popular")+  ":Check:100"
                        
	]
