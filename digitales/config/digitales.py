from frappe import _

def get_data():
	return [
		{
			"label": _("Documents"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Customer Contract Form",
					"description": _("Customer contact details.")
				},
				{
					"type": "doctype",
					"name": "Stock Assignment Log",
					"description": _("Stock assignment details.")
				},
				{
					"type": "doctype",
					"name": "API Configuration Page",
					"description": _("API timing and API type details.")
				},
				{
					"type": "doctype",
					"name": "Configuration Page",
					"description": _("Warehouse Configuration page.")
				},
				{
					"type": "doctype",
					"name": "Process",
					"label": _("Shelf Ready Charge"),
					"description": _("Shelf Ready Charge Details.")
				},
				
			]
		},

	]