function center_gallery_image(){
    // center the image vertically
    var img_url = $(".media").children("img").attr("src");
    img_url = img_url.split('_');
    img_url = img_url[img_url.length - 1];
    var img_ht = parseInt(img_url.substring(img_url.indexOf('x') + 1, img_url.indexOf('.')));
    var mar = (450 - img_ht) / 2;
    if( mar ){
        $("div.media").children("img").css("margin", mar + "px 0");
    }
}

$(document).ready(function(){
    // center image upon load
    //center_gallery_image();

    /* ========= the carousel stuff ============== */
    var num_items = $(".carousel_frame .carousel").children().length - 6;
    $(".carousel_frame .carousel").css("width", (num_items + 6) * 54);
    var cur_item = 0;
    // returns false if the slide was unsuccessful
    var slide_carousel = function(dir){
        if(cur_item + dir > num_items || cur_item + dir < 0){
            return false;
        }

        var p = parseInt($(".carousel_frame .carousel").css("left"))
        $(".carousel_frame .carousel").animate({left: p - 54 * dir}, "normal");
        cur_item += dir;
        return true;
    }

    $("#gal_left").click(function(){slide_carousel(-1)});
    $("#gal_right").click(function(){slide_carousel(1)});
    
    /* ========== changing photos in the gallery ============ */
    var _photo_cache = {};
    
    $(".carousel_frame .carousel a").click(function(e){
        var url = $(this).attr('href');
        
        // destroy the old object in the viewer area and add the new item
        var inject_results = function(results){
            var res = results.split("<!-- split -->");

            $(".media_content .media").fadeOut('fast', function(){
                $("media_content .media_info").fadeOut('fast', function(){
                    /*$(".media_content .media").empty().append(res[0]);
                    $(".media_content .media").fadeIn('fast');

                    //center_gallery_image();
                    $(".media_content .media_info").empty().append(res[1]);
                    
                    $(".media_content .media_info").fadeIn('fast');*/
                });
            });
        }        
        // look for the object in the cache, fallback on ajax
        if(_photo_cache.hasOwnProperty(url)){
            inject_results(_photo_cache[url]);
        } else {
            $.get(url, {render:'media_viewer_gallery'}, function(html){
                _photo_cache[url] = html;
                inject_results(html);
            },'html');
        }
        return false;
    });
});
