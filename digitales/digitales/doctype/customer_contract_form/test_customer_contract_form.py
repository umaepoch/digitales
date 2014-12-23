# Copyright (c) 2013, digitales and Contributors
# See license.txt

import frappe
import unittest

test_records = frappe.get_test_records('Customer Contract Form')

class TestCustomerContractForm(unittest.TestCase):
	pass
