$(document).ready(function(){
    var _media_cache = {};
    var _page_cache = {};
    var _cur_page = 1;
    var _filter_state = 0;
    var _base_url = window.location.pathname;
    var _query = $("#id_q").val()
    var _start_date = $("#id_start_date").val()
    var _end_date = $("#id_end_date").val()
    
    function inject_page(page_num){
        var inject_results = function(results){
            $(".content_list_content").fadeOut('fast', function(){
                $(this).empty()
                    .append($(results))
                    .fadeIn('fast')
            });
        };
        ajax = $.get(_base_url, {q: _query, start_date: _start_date, end_date: _end_date, ajax: '', page:_cur_page}, inject_results);
    }
    
    // pagination buttons
    $(".pagination a").live("click", function(e){
        _cur_page = $(this).attr("href").split("?")[1];
        inject_page(_cur_page);
        return false;
    });    
});