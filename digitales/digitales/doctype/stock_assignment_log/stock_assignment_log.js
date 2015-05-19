cur_frm.cscript.refresh = function(doc){
	cur_frm.toggle_enable("assign_qty", false);
	if(user=='maya@digitales.com.au'){
		cur_frm.toggle_enable("assign_qty", true);
	}
}