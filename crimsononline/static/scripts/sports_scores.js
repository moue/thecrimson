var ticker_sports = new Array();
var ticker_slugs = new Array();
var ticker_urls = new Array();


function rotateArray(arr){
    cur_item = arr.shift();
    arr.push(cur_item);
    return cur_item;
}

function rotateTicker(){
    cur_sport = rotateArray(ticker_sports);
    cur_slug = rotateArray(ticker_slugs);
    cur_url = rotateArray(ticker_urls);
    
    document.getElementById('sportsticker_sport').innerHTML = "<a href='" + cur_url + "'>" + cur_sport + "</a>";
    document.getElementById('sportsticker_slug').innerHTML = "<a href='" + cur_url + "'>" + cur_slug + " &raquo;</a>";
    t=setTimeout("rotateTicker()",5000);
}