import frappe
from frappe.utils import cstr
from .utils import log_sync_error,get_custom_attribute_value

def create_or_update_item(entity):
	""" create or update the Item """
	if not entity:
		return None

	result = {}
	try:
		name = frappe.db.get_value("Item", entity.get("sku"))
		if not name:
			item = frappe.new_doc("Item")
			item.item_code = cstr(entity.get("sku")).strip()
		else:
			item = frappe.get_doc("Item", name)

        	custom_attributes_list = entity.get("custom_attributes")#m2_changes
		item.weight_uom = "Kg"
		item.event_id = cstr(entity.get("id")) #m2_changes
		item.artist = get_custom_attribute_value(custom_attributes_list,"artist") #m2_changes
		item.item_name = cstr(entity.get('name')) or cstr(entity.get('sku'))
		item.item_group = get_item_group(get_custom_attribute_value(custom_attributes_list,"media")) #m2_changes
		item.description = 'Desc: %s'%get_custom_attribute_value(custom_attributes_list,"meta_description") if get_custom_attribute_value(custom_attributes_list,"meta_description") else  cstr(entity.get('sku'))  #m2_changes
		item.default_warehouse = get_own_warehouse()
		if get_custom_attribute_value(custom_attributes_list,"barcode") and not frappe.db.get_value('Item', { 'barcode':get_custom_attribute_value(custom_attributes_list,"barcode") }): #m2_changes
            		item.barcode = get_custom_attribute_value(custom_attributes_list,"barcode")
		item.modified_date = entity.get('updated_at')
		item.distributor = get_custom_attribute_value(custom_attributes_list,"distributor") #m2_changes
		item.product_release_date = get_custom_attribute_value(custom_attributes_list,"release_date") #m2_changes
        	item.classification = get_custom_attribute_value(custom_attributes_list,"classification") #m2_changes
		item.default_supplier = get_supplier(get_custom_attribute_value(custom_attributes_list,"distributor"))
		item.expense_account, item.income_account = default_ExpenxeIncomeAccount(item.item_group)

		item.net_weight = entity.get("weight", 0)
		item.publisher = get_custom_attribute_value(custom_attributes_list,"publisher")#m2_changes
		item.valid_from = get_custom_attribute_value(custom_attributes_list,"special_from_date") #m2_changes
		#item.valid_upto = entity.get("special_to_date") #m2_pending
		item.trade_price = get_custom_attribute_value(custom_attributes_list,"trade_price") if get_custom_attribute_value(custom_attributes_list,"trade_price") else 0 #m2_changes
		item.discounted_price = get_custom_attribute_value(custom_attributes_list,"special_price") if get_custom_attribute_value(custom_attributes_list,"special_price") else 0 #m2_changes
		item.aid_code = get_custom_attribute_value(custom_attributes_list,"aid_code") if get_custom_attribute_value(custom_attributes_list,"aid_code") else "test" #m2_changes
		item.popular= get_custom_attribute_value(custom_attributes_list,"populartag")
                #This has been added by KM on 30.03.2017 for CR ISS-00038
                #item_is_disabled = entity.get('status')
                #if item_is_disabled == 1:
                #   item.is_purchase_item="Yes"
                #else:
                #   item.is_purchase_item="No"

		item.save(ignore_permissions=True)

		create_or_update_item_price(entity)

		return {
			cstr(entity.get("sku")): {
				"operation": "Item Created" if not name else "Item Updated",
				"name": item.name,
				"modified_date": entity.get("updated_at")
			}
		}
	except Exception, e:
		docname = cstr(entity.get('sku'))
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
		if frappe.db.get_value('Customer', supplier):
			supplier = supplier + '(s)'
			temp = supplier
		name = supplier if frappe.db.get_value('Supplier', supplier) else create_supplier(supplier)
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
	sl.supplier_type = 'Stock supplier' if frappe.db.get_value('Supplier Type', 'Stock supplier') else create_supplier_type()
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

# def create_or_update_item_price(entity):
#  	# create new Item Price if not available else update
#  	price = entity.get("price")
#  	if not price:
#  		return

#  	price_list = frappe.db.get_value("Configuration Page", "Configuration Page", "price_list")
#  	if not price_list:
#  		frappe.throw("Please Specify the Price List in Configuration Page")

#  	item_price_name = frappe.db.get_value(
#  						"Item Price",
#  						{
#  							"item_code": entity.get("sku"),
#  							"price_list": price_list
#  						},
#  						"name"
#  					)

#  	if not item_price_name:
#  		item_price = frappe.new_doc("Item Price")
#  	else:
#  		item_price = frappe.get_doc("Item Price", item_price_name)

#  	item_price.item_code = cstr(entity.get("sku"))
#  	item_price.price_list = price_list
#  	item_price.price_list_rate = entity.get("price", 0)

#  	item_price.save(ignore_permissions=True)

def create_or_update_item_price(entity):
	#create new Item Price if not available else update
	price = entity.get("price")
    	custom_attributes_list = entity.get("custom_attributes") #m2_changes
	if not price:
		return

	price_list = frappe.db.get_value("Configuration Page", "Configuration Page", "price_list")
	if not price_list:
		frappe.throw("Please Specify the Price List in Configuration Page")

	item_price_name_buying = frappe.db.get_value(
						"Item Price",
						{
							"item_code": entity.get("sku"),
							"price_list": "Standard Buying"
						},
						"name"
					)
	item_price_name_selling = frappe.db.get_value(
						"Item Price",
						{
							"item_code": entity.get("sku"),
							"price_list": "Standard Selling"
						},
						"name"
					)

	if not item_price_name_buying:
		item_price_buying = frappe.new_doc("Item Price")
	else:
		item_price_buying = frappe.get_doc("Item Price", item_price_name_buying)


	if not item_price_name_selling:
		item_price_selling = frappe.new_doc("Item Price")
	else:
		item_price_selling = frappe.get_doc("Item Price", item_price_name_selling)

	item_price_buying.item_code = cstr(entity.get("sku"))
	item_price_buying.price_list = "Standard Buying"
	item_price_buying.price_list_rate = get_custom_attribute_value(custom_attributes_list,"trade_price") if get_custom_attribute_value(custom_attributes_list,"trade_price") else 0 #m2_changes

	item_price_selling.item_code = cstr(entity.get("sku"))
	item_price_selling.price_list = "Standard Selling"
	item_price_selling.price_list_rate = entity.get("price", 0)

	item_price_buying.save(ignore_permissions=True)
	item_price_selling.save(ignore_permissions=True)

