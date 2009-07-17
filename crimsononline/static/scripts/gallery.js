function center_gallery_image(){
    // center the image vertically
    var img_url = $(".viewer_image").find("img").attr("src");
    img_url = img_url.split('_');
    img_url = img_url[img_url.length - 1];
    var img_ht = parseInt(img_url.substring(img_url.indexOf('x') + 1, img_url.indexOf('.')));
    var mar = (450 - img_ht) / 2;
    if( mar ){
        $(".viewer_image").find("img").css("margin", mar + "px 0");
    }
}

$(document).ready(function(){
    // center image upon load
    center_gallery_image();

    $(".viewer_top").hover(function (){
            $(".gallery_control #inside").fadeIn("fast");
    },function (){
            $(".gallery_control #inside").fadeOut("fast");
    });


    /* ========= the carousel stuff ============== */
    var num_items = $(".carousel_frame").children().length - 6;
    var cur_item = 0;
    // returns false if the slide was unsuccessful
    var slide_carousel = function(dir){
        if(cur_item + dir > num_items || cur_item + dir < 0){
            return false;
        }

        var p = parseInt($(".carousel_frame").css("left"))
        $(".carousel_frame").animate({left: p - 54 * dir}, "normal");
        cur_item += dir;
        return true;
    }

    $("#gal_left").click(function(){slide_carousel(-1)});
    $("#gal_right").click(function(){slide_carousel(1)});
    
    /* ========== changing photos in the gallery ============ */
    var _photo_cache = new Array();
    var _des_cache = new Array();
    
    $(".carousel_frame a").click(function(e){
        var url = $(this).attr('href');
        
        // destroy the old object in the viewer area and add the new item
        var inject_results = function(top, bottom){
            $(".viewer_image").fadeOut('fast', function(){
                $(".viewer_info").fadeOut('fast', function(){
                    $(".viewer_image").empty().append(top);
                    $(".viewer_image").fadeIn('fast');
                    $(".viewer_info").empty().append(bottom);
                    $(".viewer_info").fadeIn('fast');
                    center_gallery_image();
                });
            });
        }        
        // look for the object in the cache, fallback on ajax
        if(!_photo_cache.hasOwnProperty(url)){
            $.get(url, {render:'gallery_top'}, function(html){
                _photo_cache[url] = html;
                $.get(url, {render:'gallery_bottom'}, function(html){
                    _des_cache[url] = html;
                    inject_results(_photo_cache[url], _des_cache[url]);
                },'html');
            },'html');
        }
        else{
            inject_results(_photo_cache[url], _des_cache[url]);
        }
        return false;
    });
});
