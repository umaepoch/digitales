# Copyright (c) 2013, digitales and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt
from frappe.model.document import Document

class StockAssignmentLog(Document):
	def validate(self):
		self.delivered_qty = cint(self.delivered_qty)
		self.assigned_qty_validation()
		self.update_qty_in_sales_order()
		if not self.get("__islocal") and self.name:
			self.check_qty_equal()

	def assigned_qty_validation(self):
		if flt(self.ordered_qty) < flt(self.assign_qty):
			frappe.throw(_('Assigned qty must be less than ordered qty for item code {0} in sales order {1}').format(self.item_code, self.sales_order))

	def check_qty_equal(self):
		sum_qty = 0
		sum_qty = sum(d.qty for d in self.get('document_stock_assignment'))
		if cint(self.assign_qty) != cint(sum_qty):
			frappe.throw(_('Assigned qty must be equl to the sum of qty in Document Wise History table for item code {0}').format(self.item_code))

	def update_qty_in_sales_order(self):
		self.assign_qty = self.assign_qty if self.assign_qty else 0
		if self.sales_order and self.item_code:
			frappe.db.sql(''' update `tabSales Order Item` set assigned_qty = "%s" where
				parent = "%s" and item_code ="%s"'''%(self.assign_qty, self.sales_order, self.item_code))
			


