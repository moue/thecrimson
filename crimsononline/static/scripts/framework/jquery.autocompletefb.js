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


jQuery.fn.autoCompletefb = function(options) 
{
	var tmp = this;
	var settings = 
	{
		ul            : tmp,
		urlLookup     : [""],
		acOptions     : {formatItem: function(row, row_num, rows, q_str){
		    return row[1];}, matchContains: true},
		foundClass    : ".acfb-data",
		inputClass    : ".acfb-input",
        multipleInput : false,
        no_duplicates : true
	};
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
			$(settings.inputClass,tmp).show().focus();
			return tmp.acfb;
		},
		dumpData : function(){
		    $(settings.inputClass,tmp).parent().next().val(this.getData());
		    $(settings.inputClass,tmp).flushCache();
		},
        disableInput : function(){
            $(settings.inputClass,tmp).val('').hide();
        },
        insertItem : function(pk, label){
            //force insert. if there's already an element and only 1 element
            //  is allowed, remove the previous element.
            if(!settings.multipleInput && acfb.getData()){
                acfb.removeFind($(settings.inputClass, tmp).parent().prev());
            }            
            label = label+" ";
            var c = settings.foundClass.replace(/\./,'');
    		var v = '<li class="'+c+'"><span class="label">'+label+'</span><span class="pk" style="display:none">'+pk+'</span><img class="p" src="/site_media/images/delete.gif"/></li>';
    		var x = $(settings.inputClass,tmp).parent().before(v);
    		$('.p',x[0].previousSibling).click(function(){
    			acfb.removeFind(this);
    		});
            if(settings.multipleInput){
                $(settings.inputClass,tmp).val('').focus();
            } else {
                acfb.disableInput();
            }
    		acfb.dumpData();
        }
	};
	
	if(settings.no_duplicates){
	    settings.acOptions['extraParams'] = {exclude: function(){
	        return acfb.getData();
        }};
	}
	
	$(settings.foundClass+" img.p",tmp).click(function(){
		acfb.removeFind(this);
	});
	
	$(settings.inputClass,tmp).autocomplete(settings.urlLookup,settings.acOptions);
	$(settings.inputClass,tmp).result(function(e,d,f){
	    var pk = d[0];
	    var label = d[1];
		acfb.insertItem(pk, label);
	});
    if(acfb.getData() && !settings.multipleInput){
        acfb.disableInput();
    }
	// focus cursor correctly in the fake input borders
	$(settings.inputClass,tmp).parent().parent().click(function(){
	    if(settings.multipleInput || !acfb.getData()){
	        $(settings.inputClass,tmp).focus();
	    } else if(! $(".acfb-warning",tmp).html() ){
	        ele = $('<li class="acfb-warning">You can only enter one value here.</li>');
	        $(ele)
	            .insertAfter($(settings.inputClass,tmp))
	            .fadeTo(2000, 1, function(){
	                $(this).fadeOut("slow", function(){$(this).remove()
	            })
	        });
	    }
	});
	
	return acfb;
}
