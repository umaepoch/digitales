// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('customer','customer_name','customer_name');


cur_frm.cscript.contract_start_date = function(doc,cdt,cdn){
	if (doc.contract_start_date && doc.contract_end_date){
		var date1 = new Date(doc.contract_start_date);
		var date2 = new Date(doc.contract_end_date);
		if(date1>date2){
			msgprint("Contract Start Date must be less than Contract End Date")
		}
	}
}


cur_frm.cscript.contract_end_date = function(doc,cdt,cdn){
	if (doc.contract_start_date && doc.contract_end_date){
		var date1 = new Date(doc.contract_start_date);
		var date2 = new Date(doc.contract_end_date);
		if(date2<date1){
			msgprint("Contract End Date must be greater than Contract Start Date")
		}
	}
}