// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt





cur_frm.get_field("process_type").get_query=function(doc,cdt,cdn){

	return {filters: { is_service_item: "Yes"}}

}
