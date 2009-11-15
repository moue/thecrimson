var media_list = new Array();


function require_once(url) {
    if(typeof(media_list[url]) == 'undefined'){
        media_list[url]=true;
        document.write('<script type="text/javascript" src="' + url + '"></script>');
    }
}