/*
 * jQuery plugin: autoCompletefb(AutoComplete Facebook)
 * @requires jQuery v1.2.2 or later
 * using plugin:jquery.autocomplete.js
 *
 * Credits:
 * - Idea: Facebook
 * - Guillermo Rauch: Original MooTools script
 * - InteRiders <http://interiders.com/> 
 *
 * Copyright (c) 2008 Widi Harsojo <wharsojo@gmail.com>, http://wharsojo.wordpress.com/
 * Dual licensed under the MIT and GPL licenses:
 *   http://www.opensource.org/licenses/mit-license.php
 *   http://www.gnu.org/licenses/gpl.html
 */

/* TODO: make this eliminate duplicates entries */

jQuery.fn.autoCompletefb = function(options) 
{
	var tmp = this;
	var settings = 
	{
		ul         : tmp,
		urlLookup  : [""],
		acOptions  : {formatItem: function(row, row_num, rows, q_str){
		    return row[1];
		}},
		foundClass : ".acfb-data",
		inputClass : ".acfb-input"
	}
	if(options) jQuery.extend(settings, options);
	
	var acfb = 
	{
		params  : settings,
		getData : function()
		{	
			var result = '';
		    $(settings.foundClass,tmp).each(function(i)
			{
				if (i>0)result+=',';
			    result += $('.pk',this).html();
		    });
			return result;
		},
		clearData : function()
		{	
		    $(settings.foundClass,tmp).remove();
		    this.dumpData();
			$(settings.inputClass,tmp).focus();
			return tmp.acfb;
		},
		removeFind : function(o){
			$(o).unbind('click').parent().remove();
			this.dumpData();
			$(settings.inputClass,tmp).focus();
			return tmp.acfb;
		},
		dumpData : function(){
		    $(settings.inputClass,tmp).next().val(this.getData());
		}
	}
	
	$(settings.foundClass+" img.p").click(function(){
		acfb.removeFind(this);
	});
	
	$(settings.inputClass,tmp).autocomplete(settings.urlLookup,settings.acOptions);
	$(settings.inputClass,tmp).result(function(e,d,f){
	    var pk = d[0];
	    var label = d[1]+" ";
		var c = settings.foundClass.replace(/\./,'');
		var v = '<li class="'+c+'"><span class="label">'+label+'</span><span class="pk" style="display:none">'+pk+'</span><img class="p" src="/site_media/images/delete.gif"/></li>';
		var x = $(settings.inputClass,tmp).before(v);
		$('.p',x[0].previousSibling).click(function(){
			acfb.removeFind(this);
		});
		acfb.dumpData();
		$(settings.inputClass,tmp).val('').focus();
	});
	$(settings.inputClass,tmp).focus();
	return acfb;
}
