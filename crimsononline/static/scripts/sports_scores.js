var ticker_sports = new Array();
var ticker_slugs = new Array();
var ticker_urls = new Array();
var ticker_opp = new Array();
var ticker_field = new Array();
var ticker_oppscore = new Array();
var ticker_ourscore = new Array();

function rotateArray(arr){
    cur_item = arr.shift();
    arr.push(cur_item);
    return cur_item;
}

function rotateTicker(){
    cur_sport = rotateArray(ticker_sports);
    cur_slug = rotateArray(ticker_slugs);
    cur_url = rotateArray(ticker_urls);
	cur_opp = rotateArray(ticker_opp);
	cur_field = rotateArray(ticker_field);
	cur_oppscore = rotateArray(ticker_oppscore);
	cur_ourscore = rotateArray(ticker_ourscore);
	
	var first, second, firstscore, secondscore;

	if (cur_field)
	{
		first = "Harvard";
		second = cur_opp;
		firstscore = cur_ourscore;
		secondscore = cur_oppscore;
	}
	else
	{
		first = cur_opp;
		second = "Harvard";
		firstscore = cur_oppscore;
		secondscore = cur_ourscore;
	}	
    
    document.getElementById('sportsticker_sport').innerHTML = "<a href='" + cur_url + "'>" + cur_sport + "</a>";
    
	if (cur_oppscore == "")
		document.getElementById('sportsticker_slug').innerHTML = "<a href='" + cur_url + "'>" + cur_slug + " &raquo;</a>";
	else
		document.getElementById('sportsticker_slug').innerHTML = "<a href='" + cur_url + "'>" + "<b>" + first + "</b>" + " " + firstscore + " <b>" + second + "</b> " + secondscore + " &raquo;</a>";
    t=setTimeout("rotateTicker()",3000);
}