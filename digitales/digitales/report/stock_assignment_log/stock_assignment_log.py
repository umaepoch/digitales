# Copyright (c) 2013, digitales and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	# columns, data = [], []
	# return columns, data
	columns = get_columns()
	data = get_stock_assignment_log_data(filters)

	return columns, data

def get_columns():
	return [
			# _("Picked") + ":Check:100",
			_("ID") + ":Link/Stock Assignment Log:100",
			_("Sales Order") + ":Link/Sales Order:100",
			_("New Order Type") + "::100",
			_("Priority") + "::100",
			_("Customer Name") + "::200",
			_("Item Code") + ":Link/Item:100",
			_("Item Name") + "::200",
			_("Media") + "::100",
			_("Type") + "::100",
			_("Budget") + ":Link/Budget:100",
			_("Stock Assign/Receive Date") + "::100",
			_("Ordered Qty") + "::100",
			_("Assigned Qty") + "::100",
			_("Total Assigned Qty") + "::100",
			_("Delivered Qty") + "::100"
			]

def get_stock_assignment_log_data(filters):
	return frappe.db.sql("""SELECT 	#sal.picked as picked,
									sal.name AS id,
									sal.sales_order AS sales_order,
									so.order_type AS order_type,
									so.priority AS priority,
									sal.customer_name AS customer_name,
									sal.item_code AS item_code,
									sal.item_name AS item_name,
									i.item_group AS media,
									dsa.document_type AS type,
									so.budget AS budget,
									dsa.created_date AS dsa_date,
									sal.ordered_qty AS ordered_qty,
									dsa.qty AS assigned_qty,
									(
										SELECT
											 sum(qty)
										FROM
										    `tabDocument Stock Assignment` d
										WHERE
											d.parent=dsa.parent AND (d.idx=1 or d.idx<=dsa.idx)
									) AS Total_Qty,
									format(ifnull(sal.delivered_qty,0),0) as delivered_qty
							FROM 
								`tabDocument Stock Assignment` AS dsa
							JOIN
								`tabStock Assignment Log` AS sal
							ON
								sal.name = dsa.parent
							JOIN
								`tabSales Order` AS so
							ON
								so.name = sal.sales_order
							JOIN
								`tabItem` AS i
							ON
								i.item_code = sal.item_code
							WHERE dsa.created_date between '{0}' and '{1}' {conditions}
							ORDER BY 
								sal.sales_order DESC, sal.item_code ASC,dsa.created_date
						""".format(filters['from_date'],filters['to_date'],conditions=get_conditions(filters)))

def get_conditions(filters):
	conditions = []
	for key in filters:
		if filters.get(key) and key not in ['from_date', 'to_date']:
			conditions.append("sal.%s = '%s'"%(key, filters.get(key)))

	return " and {}".format(" and ".join(conditions)) if conditions else ""