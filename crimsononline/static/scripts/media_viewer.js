// functions for media viewer page
$(document).ready(function(){
    var _media_cache = {};
    var _page_cache = {};
    
    // pagination buttons
    $("#media_viewer span.pagination a").live("click", function(e){
        var page_num = $(this).attr("href").split("#")[1];
        
        var inject_results = function(results){
            $("#media_viewer #viewer_sidebar > div").fadeOut('fast', function(){
                $(this).empty().append($(results)).fadeIn('fast');
            });
        }
        
        // look for the object in the cache, fallback on ajax
        if(_page_cache.hasOwnProperty(page_num)){
            inject_results(_media_cache[page_num]);
        } else {
            $.get('/section/photo/', {page: page_num, ajax:''}, inject_results, function(html){
                _page_cache[page_num] = html;
                inject_results(html);
            }, 'html');
        }
        return false;
    });
    
    // loading media from the sidebar
    $("#media_viewer #viewer_sidebar ul a").live("click", function(e){
        // where to load the resource from 
        var url = $(this).attr("href");
        
        // destroy the old object in the viewer area and add the new item
        var inject_results = function(results){            
            $("#viewer_main").fadeOut('fast', function(){
                $(this).empty().append($(results)).fadeIn('fast');
            });
        }
        
        // look for the object in the cache, fallback on ajax
        if(_media_cache.hasOwnProperty(url)){
            inject_results(_media_cache[url]);
        } else {
            $.get(url, {render:'media_viewer'}, inject_results, function(html){
                _media_cache[url] = html;
                inject_results(html);
            }, 'html');
        }
        return false;
    });
});