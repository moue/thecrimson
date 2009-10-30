$(document).ready(function(){
    var _media_cache = {};
    var _page_cache = {};
    var _cur_page = 1;
    var _cur_sections = [];
    var _cur_types = [];
    var _filter_state = 0;
    var _base_url = window.location.pathname;

    // set initial value for sections
    initial_sections = function(){
        $(".filter_section input:checked").each(
            function(){
                _cur_sections.push($(this).attr('name'));      
            });
    };
    
    // set initial value for types
    initial_types = function(){
        $(".filter_type input:checked").each(
            function(){
                _cur_types.push($(this).attr('name'));      
            });
    };
    initial_sections();
    initial_types();
    
    function inject_page(page_num, sections, types){
        var inject_results = function(results){
            $(".content_list_content").fadeOut('fast', function(){
                $(this).empty()
                    .append($(results))
                    .fadeIn('fast')
            });
        };
        ajax = $.get(_base_url + 'page/' + page_num, {ajax: '', sections: sections.join(","), 
            types: types.join(",")}, inject_results);
    }
    
    // pagination buttons
    $(".pagination a").live("click", function(e){
        _cur_page = $(this).attr("href").split("?")[1];
        inject_page(_cur_page, _cur_sections, _cur_types);
        return false;
    });
    
    // section buttons
    $(".filter_section input").live("click", function(e){
        section = $(this).attr('name');
        if($(this).is(':checked')){
            _cur_sections.push(section);
        }
        else
        {
            _cur_sections.splice(_cur_sections.indexOf(section), 1);
        }
        if(_cur_sections.length == 0){
            $(".filter_section input").attr("checked",true);
            initial_sections();
        }
        inject_page(_cur_page, _cur_sections, _cur_types)
    });

    // type buttons
    $(".filter_type input").live("click", function(e){
        type = $(this).attr('name');
        if($(this).is(':checked')){
            _cur_types.push(type);
        }
        else
        {
            _cur_types.splice(_cur_types.indexOf(type), 1);
        }
        if(_cur_types.length == 0){
            $(".filter_type input").attr("checked",true);
            initial_types();
        }
        inject_page(_cur_page, _cur_sections, _cur_types)
    });
    
    
    /* Filter sliding effects */
    $("a#filter_toggle").click(function () {
        if ($("#filter_toggle_contents").is(":hidden")) {
            $("#filter_toggle_contents").slideDown("slow");
            $(this).text("Hide Filters");
        } else {
            $("#filter_toggle_contents").slideUp("slow");
            $(this).text("Filter");
        }
    });
    
});