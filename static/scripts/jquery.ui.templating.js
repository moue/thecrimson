(function ($) {
	  $.makeTemplate = function (template, begin, end) {
	    var rebegin = begin.replace(/([\]{}[\\])/g, '\\$1');
	    var reend = end.replace(/([\]{}[\\])/g, '\\$1');
	
	    var code = "try { with (_context) {" +
	      "var _result = '';" +
	        template
	          .replace(/[\t\r\n]/g, ' ')
	          .replace(/^(.*)$/, end + '$1' + begin)
	          .replace(new RegExp(reend + "(.*?)" + rebegin, "g"), function (text) {
	            return text
	              .replace(new RegExp("^" + reend + "(.*)" + rebegin + "$"), "$1")
	              .replace(/\\/g, "\\\\")
	              .replace(/'/g, "\\'")
	              .replace(/^(.*)$/, end + "_result += '$1';" + begin);
	          })
	          .replace(new RegExp(rebegin + "=(.*?)" + reend, "g"), "_result += ($1);")
	          .replace(new RegExp(rebegin + "(.*?)" + reend, "g"), ' $1 ')
	          .replace(new RegExp("^" + reend + "(.*)" + rebegin + "$"), '$1') +
	      "return _result;" +
	    "} } catch(e) { return '' } ";
	
	    return new Function("_context", code);
	  };
	})(jQuery);