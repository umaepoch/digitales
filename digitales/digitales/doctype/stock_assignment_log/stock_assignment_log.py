# Copyright (c) 2013, digitales and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt
from frappe.model.document import Document

class StockAssignmentLog(Document):
	def validate(self):
		self.assigned_qty_validation()
		self.update_qty_in_sales_order()
		if not self.get("__islocal"):
			self.check_qty_equal()

	def assigned_qty_validation(self):
		if flt(self.ordered_qty) < flt(self.assign_qty):
			frappe.throw(_('Assigned qty must be less than ordered qty'))

	def check_qty_equal(self):
		sum_qty = 0
		sum_qty = sum(d.qty for d in self.get('document_stock_assignment'))
		if cint(self.assign_qty) != cint(sum_qty):
			frappe.throw(_('Assigned qty must be equl to the sum of qty in Document Wise History table'))

	def update_qty_in_sales_order(self):
		if self.sales_order and self.item_code and self.assign_qty:
			frappe.db.sql(''' update `tabSales Order Item` set assigned_qty = "%s" where
				parent = "%s" and item_code ="%s"'''%(self.assign_qty, self.sales_order, self.item_code))



