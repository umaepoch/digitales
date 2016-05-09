import frappe
from .utils import (date_minus_sec, get_entity_and_page_count, get_entities_from_magento,
	log_sync_status) 
from digitales.digitales.Api_methods import update_execution_date, log_sync_error

def get_products():
	""" 
		get newly created / updated product from magento
		fetch the product based on updated_at field in magento
	"""
	count = {}
	sync_stat = {}
	page_count = 0
	total_items_to_sync = 0
	try:
		max_date = frappe.db.sql("select max(modified_date) as max_date from tabItem", as_dict=True)
		max_date = "1991-09-07 05:43:13" if not max_date else max_date[0].get("max_date")
		count = get_entity_and_page_count(max_date, entity_type="Item")
		if not count:
			return

		total_items_to_sync = count.get("entity_count")
		page_count = count.get("page_count") + 1 if count.get("page_count") else 0

		url = "http://digitales.com.au/api/rest/products?filter[1][attribute]=updated_at"
		url += "&filter[1][gt]={}&page={}&limit=100&order=updated_at&dir=asc"
		for idx in xrange(1, page_count):
			response = get_entities_from_magento(url.format(date_minus_sec(max_date), idx), entity_type="Item")
			if not response:
				continue

			sync_stat = { entity_id: { "modified_date": entity.get("updated_at") } for entity_id, entity in response.iteritems() }
			for entity_id, item in response.iteritems():
				status = create_or_update_item(item)
				sync_stat.update(status)
				# frappe.db.commit()
	except Exception, e:
		print frappe.get_traceback()
		raise e
	finally:
		log_sync_status(
			"Item", count_response=count, entities_to_sync=total_items_to_sync, 
			pages_to_sync=page_count, synced_entities=sync_stat
		)
		update_execution_date('Customer')

def create_or_update_item(entity):
	""" create or update the Item """
	if not entity:
		return None

	result = {}
	try:
		name = frappe.db.get_value("Item", entity.get("sku"))
		if not name:
			item = frappe.new_doc("Item")
			item.item_code = entity.get("sku")
		else:
			item = frappe.get_doc("Item", name)

		item.event_id = entity.get("entity_id")
		item.artist = entity.get('artist')
		item.item_name = entity.get('name') or entity.get('sku')
		item.item_group = get_item_group(entity.get('media'))
		item.description = 'Desc: %s'%entity.get('short_description') if entity.get('short_description') else entity.get('sku')
		item.default_warehouse = get_own_warehouse()
		if entity.get('barcode') and not frappe.db.get_value('Item', {'barcode':entity.get('barcode')}, 'name'):
			item.barcode = entity.get('barcode')
		item.modified_date = entity.get('updated_at')
		item.distributor = entity.get('distributor')
		item.product_release_date = entity.get('release_date')
		item.default_supplier = get_supplier(entity.get('distributor'))
		item.expense_account, item.income_account = default_ExpenxeIncomeAccount(item.item_group)

		item.save(ignore_permissions=True)

		return {
			entity.get("entity_id"): {
				"operation": "Item Created" if not name else "Item Updated",
				"name": item.name,
				"modified_date": entity.get("updated_at")
			}
		}
	except Exception, e:
		docname = entity.get('sku')
		response = entity
		log_sync_error("Item", docname, response, e, "create_item")

def get_item_group(item_group):
	""" get or create item group """
	media = 'Products'
	if item_group:
		media = item_group.split(',')[0]
		if not frappe.db.get_value('Item Group', media, 'name'):
			doc = frappe.new_doc('Item Group')
			doc.parent_item_group = 'All Item Groups'
			doc.item_group_name = item_group
			doc.is_group = 'No'
			doc.save(ignore_permissions=True)
			media = doc.name

	return media

def get_own_warehouse():
	""" get default warehouse """
	warehouse = frappe.db.get_value("Configuration Page", "Configuration Page", "own_warehouse")

	if not warehouse:
		frappe.throw("Please specify default own warehouse in Configuration Page")
	else:
		return warehouse

def get_supplier(supplier):
	temp = ''
	if supplier:
		if frappe.db.get_value('Customer', supplier, 'name'):
			supplier = supplier + '(s)'
			temp = supplier
		name = supplier if frappe.db.get_value('Supplier', supplier, 'name') else create_supplier(supplier)
		if temp:
			update_supplier(supplier)
		return name
	return ''

def update_supplier(supplier):
	obj = frappe.get_doc('Supplier', supplier)
	obj.supplier_name = supplier.replace('(s)', '')
	obj.save(ignore_permissions=True)

def create_supplier(supplier):
	sl = frappe.new_doc('Supplier')
	sl.supplier_name = supplier
	sl.supplier_type = 'Stock supplier' if frappe.db.get_value('Supplier Type', 'Stock supplier', 'name') else create_supplier_type()
	sl.save(ignore_permissions=True)
	return sl.name

def create_supplier_type():
	st = frappe.new_doc('Supplier Type')
	st.supplier_type = 'Stock supplier'
	st.save(ignore_permissions=True)
	return st.name

def default_ExpenxeIncomeAccount(media):
	# Check item group and assign the default expence and income account
	expense_account, income_account = '', ''
	if media in ['DVD', 'CD', 'BLURAY', 'Graphic Novel', 'CDROM', 'Audio Book', 'Manga',
				'Online Resource', 'Blu-Ray', 'PC Games', 'Hardcover', 'Playstation 3',
				'Xbox 360', 'Xbox One', 'Playstation 4', 'Nintendo Wii U', '2CD and DVD',
				'Graphics', '3D', 'UV', 'BLURAY, 3D', 'Nintendo 3DS', 'Nintendo Wii', 'DVD, UV',
				'BLURAY, DVD', 'BLURAY, DVD, UV', 'Playstation Vita', 'Paperback']:
		expense_account = "5-1100 Cost of Goods Sold : COGS Stock"
		income_account = "4-1100 Product Sales"

	return expense_account, income_account