$(document).ready(function(){
    var _media_cache = {};
    var _page_cache = {};

    // pagination buttons
    $(".pagination a").live("click", function(e){
        var link = $(this).attr("href");
            
        var inject_results = function(results){
            $(".content_list_content").fadeOut('fast', function(){
                $(this).empty().append($(results)).fadeIn('fast');
            });
        }
        // TODO: cache like media viewer
        $.get(link, {ajax:''}, inject_results, 'html');
        return false;
    });

    // TODO: GET THIS TO UPDATE URLS FOR THE BUTTONS. DISABLE THIS FEATURE UNTIL THEN
    /*
    // section buttons
    $("a.section").live("click", function(e){
        var link = $(this).attr("href");
            
        var inject_results = function(results){
            $(".content_list .content").fadeOut('fast', function(){
                $(this).empty().append($(results)).fadeIn('fast');
            });
        }
        // TODO: cache like media viewer
        $.get(link, {ajax:''}, inject_results, function(html){
            inject_results(html);
        }, 'html');
        
        if($(this).find("span").hasClass("thclabel_red")){
            $(this).find("span").removeClass("thclabel_red")
            $(this).find("span").addClass("thclabel_gray")
        }
        else{
            $(this).find("span").removeClass("thclabel_gray")
            $(this).find("span").addClass("thclabel_red")
        }
        
        return false;
    });*/

    /* Filter sliding effects */
    $("#filter_toggle").click(function () {
        if ($("#filter_contents").is(":hidden")) {
                $("#filter_contents").slideDown("slow");
                $(this).text("Hide Filters")
              } else {
                $("#filter_contents").slideUp("slow");
                $(this).text("Show Filters")
              }
    });
    
});