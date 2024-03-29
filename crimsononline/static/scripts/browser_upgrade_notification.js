/**
 * If the web browser is IE6 or below, display a close-able little notice bar 
 * on the top of the web page, to notify user to upgrade to a better browser.
 *
 * Usage: Simply include this file in the pages that you want the notice bar appear.
 * 
 * Hesky Ji<hji003@gmail.com>
 * Maikel Daloo<maikel.daloo@gmail.com> 
 *
 * public-beta-0.1
 * 11/08/2008
 */

var ua = navigator.userAgent.toLowerCase();
var client = {
    isStrict:   document.compatMode == 'CSS1Compat',
    isOpera:    ua.indexOf('opera') > -1,
    isIE:       ua.indexOf('msie') > -1,
    isIE2:      ua.indexOf('msie 2') > -1,
    isIE3:      ua.indexOf('msie 3') > -1,
    isIE4:      ua.indexOf('msie 4') > -1,
    isIE5:      ua.indexOf('msie 5') > -1,
    isIE6:      ua.indexOf('msie 6') > -1,
    isIE7:      ua.indexOf('msie 7') > -1,
    isIE8:      ua.indexOf('msie 8') > -1,
    isSafari:   /webkit|khtml/.test(ua),
    isWindows:  ua.indexOf('windows') != -1 || ua.indexOf('win32') != -1,
    isMac:      ua.indexOf('macintosh') != -1 || ua.indexOf('mac os x') != -1,
    isLinux:    ua.indexOf('linux') != -1,
	isFF:		ua.indexOf('firefox/2') != -1
};
client.isBorderBox = client.isIE && !client.isStrict;
client.isSafari3 = client.isSafari && !!(document.evaluate);
client.isGecko = ua.indexOf('gecko') != -1 && !client.isSafari;

/**
 * You're not sill using IE6 are you?
 *
 * @var         Boolean
 * @private
 */
var ltIE7 = (client.isIE6 || client.isIE5 || client.isIE4 || client.isIE3 || client.isIE2) || client.isFF;

if(ltIE7){
  addLoadEvent(display_warning);
}

function addLoadEvent(func) {
  var oldonload = window.onload;
  if (typeof window.onload != 'function') {
    window.onload = func;
  } else {
    window.onload = function() {
      func();
      if (oldonload) {
        oldonload();
      }
    }
  }
}
  
function display_warning(){
  var oldHtml = document.body.innerHTML;
  var css_a = 'text-decoration: underline; color: black; font-weight:bold;';
  var warningHtml = "";
  warningHtml += '<style>';
  warningHtml += 'html, body { ';
  warningHtml += 'overflow-y: hidden!important; ';
  warningHtml += 'height: 100%;';
  warningHtml += 'padding: 0px;';
  warningHtml += 'margin: 0px;';
  warningHtml += '</style>';
  warningHtml += "<div style='position: absolute; top:0px; bottom:auto; left:0px; right:0px; margin: 0px; height:17px; padding: 3px; font-family: Verdana, Helvetica, Geneva, Arial, sans-serif; font-size:15px; background-color:#FFFFE1; color:black; border-top: 1px solid #FFFFE1; border-bottom: 1px solid #cccccc; padding-left:15px; margin-left: -15px;'>";
  warningHtml += "<div style='float:right; text-align:right; width:50px; margin: auto 5px;'>";
  warningHtml += "<a style='text-decoration: none; color: black;' href='#close' onclick='this.parentNode.parentNode.style.display=\"none\"; this.parentNode.parentNode.parentNode.childNodes[0].childNodes[0].style.display=\"none\"; return false;'>[close]</a>";
  warningHtml += "</div>";
  warningHtml += "<div style='text-align:left; margin:auto 10px;'>";
  warningHtml += "You are using an out-of-date browser version. Please upgrade! Many features of our new site may not be supported in your browser.";
  warningHtml += "</div>";
  warningHtml += "</div>";
  var spacerHTML = "";
  spacerHTML += "<div style='height:25px; line-height:25px; font-size:10px; display:block; margin:0px; padding:0px;'>";
  spacerHTML += "</div>";
  var oldHTMLWrap = "";
  oldHTMLWrap += "<div style='width:100%; margin:0px; padding:0px; height:100%; overflow-y: scroll; position:relative;'>";
  oldHTMLWrap += spacerHTML;
  oldHTMLWrap += oldHtml;
  oldHTMLWrap += "</div>";
  document.body.innerHTML = oldHTMLWrap + warningHtml;
}
