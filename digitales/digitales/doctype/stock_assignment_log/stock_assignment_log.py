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
		self.check_duplicate()
		self.check_item_code_available_in_So()
		if not self.get("__islocal") and self.name:
			self.check_qty_equal()

	def assigned_qty_validation(self):
		if flt(self.ordered_qty) < flt(self.assign_qty):
			frappe.throw(_('Assigned qty must be less than ordered qty for item code {0}, sales order {1} in SAL #{2}').format(self.item_code, self.sales_order, self.name))

	def check_qty_equal(self):
		sum_qty = 0
		sum_qty = sum(d.qty for d in self.get('document_stock_assignment'))
		if cint(self.assign_qty) != cint(sum_qty):
			frappe.throw(_('Assigned qty must be equl to the sum of qty in Document Wise History table for item code {0} in SAL #{1}').format(self.item_code, self.name))

	def update_qty_in_sales_order(self):
		self.assign_qty = self.assign_qty if self.assign_qty else 0
		if self.sales_order and self.item_code:
			frappe.db.sql(''' update `tabSales Order Item` set assigned_qty = "%s" where
				parent = "%s" and item_code ="%s"'''%(self.assign_qty, self.sales_order, self.item_code))

	def check_duplicate(self):
		if self.sales_order and self.item_code:
			SAL_details = frappe.db.sql(''' select name from `tabStock Assignment Log` 
				where sales_order = "%s" and item_code = "%s" and name != "%s"'''%(self.sales_order, self.item_code, self.name))
			if SAL_details:
				frappe.throw(_("Already Stock assignment created"))

	def check_item_code_available_in_So(self):
		if self.sales_order and self.item_code:
			get_details = self.get_so_item_details()
			if not get_details:
				frappe.throw(_("Item code not available in sales order"))


	def on_trash(self):
		self.update_SAL()

	def update_SAL(self):
		item_details = self.get_so_item_details()
		assign_qty = cint(self.assign_qty) if cint(self.assign_qty) > 0 else cint(item_details.get("qty", 0))
		val = cint(item_details.get("qty", 0)) - assign_qty
		frappe.db.sql(''' update `tabSales Order Item` set assigned_qty = %s
			where parent = "%s" and item_code = "%s"'''%(val, self.sales_order, self.item_code))

	def get_item_details(self):
		if self.sales_order:
			so_details = self.get_so_item_details()
			if so_details:
				self.media = so_details.item_group
				self.item_name = so_details.item_name
				self.ordered_qty = so_details.qty
			else:
				frappe.throw(_("Selected item {0} not present in the sales order {1}").format(self.item_code, self.sales_order))	
		else:
			frappe.throw(_("Select the sales order first"))
		return True

	def get_so_item_details(self):
		return frappe.db.get_value('Sales Order Item', {'parent': self.sales_order,'item_code': self.item_code}, '*', as_dict =1) or {}