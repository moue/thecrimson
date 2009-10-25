// functions for media viewer page
$(document).ready(function(){
    var _media_cache = {};
    var _page_cache = {};
    var _cur_sort = "recent";
    var _cur_sections_default = ["news","sports","fm","arts"];
    var _cur_sections = _cur_sections_default.slice(0);
    
    // sort/filter buttons
    // TODO: add filtering
    // TODO: destroy page cache when switching ordering
    
    function inject_sidebar(page_num, sortby, sections){
        $("#viewer_sidebar > div").fadeOut('fast');
        var inject_results = function(results){
            $("#viewer_sidebar > div").empty()
                                      .append($(results))
                                      .fadeIn('fast');
        };
        ajax = $.get('/section/photo/', {ajax: '', sort: sortby, 
            page:page_num, sections: sections.join(",")} , inject_results);
    }
    
    // sorting
    $("#sort_filters a").live("click", function(e){
        var sortby = $(this).attr("href");
        _cur_sort = sortby;
            
        $('#sort_filters a').find('span').removeClass("thclabel_blacktive");
        $('#sort_filters a').find('span').addClass("thclabel_black");
        $(this).find('span').removeClass("thclabel_black");
        $(this).find('span').addClass("thclabel_blacktive");
        
        inject_sidebar(1, _cur_sort, _cur_sections);
        
        return false;
    });
    
    // filtering by section
    $("#section_filters a").live("click", function(e){
        var section = $(this).attr("href");

        // section needs to be added
        if(_cur_sections.indexOf(section) == -1){
            $(this).find('span').removeClass("thclabel_black");
            $(this).find('span').addClass("thclabel_blacktive");
            _cur_sections.push(section);
        }
        // removed
        else{
            $(this).find('span').removeClass("thclabel_blacktive");
            $(this).find('span').addClass("thclabel_black");
            _cur_sections.splice(_cur_sections.indexOf(section), 1);
        }
    
        // if nothing is selected, select everything
        if(_cur_sections.length==0){
            // copy default array
            _cur_sections = _cur_sections_default.slice(0);
            $('#section_filters a').find('span').removeClass("thclabel_black"); 
            $('#section_filters a').find('span').addClass("thclabel_blacktive");
        }
        
        inject_sidebar(1, _cur_sort, _cur_sections);
        
        return false;
    });
    
    
    // pagination buttons
    $(".pagination a").live("click", function(e){
        var page_num = $(this).attr("href").split("#")[1];

        /*
        // look for the object in the cache, fallback on ajax
        if(_page_cache.hasOwnProperty(page_num)){
            inject_results(_media_cache[page_num]);
        } else {
            $.get('/section/photo/', {page: page_num, ajax:''}, inject_results, function(html){
                _page_cache[page_num] = html;
                inject_results(html);
            }, 'html');
        }*/
        
        inject_sidebar(page_num, _cur_sort, _cur_sections);
        
        return false;
    });
    
    // loading media from the sidebar
    $("#viewer_sidebar ul a").live("click", function(e){
        // where to load the resource from 
        var url = $(this).attr("href");
        
        // destroy the old object in the viewer area and add the new item
        $("#viewer_main").fadeOut('fast');
        var inject_results = function(results){            
            $("#viewer_main").empty().append($(results)).fadeIn('fast');
        };
        
        // look for the object in the cache, fallback on ajax
        if(_media_cache.hasOwnProperty(url)){
            inject_results(_media_cache[url]);
        } else {
            $.get(url, {render:'media_viewer'}, inject_results, function(html){
                _media_cache[url] = html;
                inject_results(html);
            }, 'html');
        }
        
        // make active gallery highlight
        $("#viewer_sidebar").find("li.active").removeClass("active");
        $(this).parent().parent().addClass("active");
        
        return false;
    });
});