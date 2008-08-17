$(document).ready(function(){
    //TODO: hide the SelectMultiple field
    
    // prefix of the url from which to grab images
    var image_req_url = "/admin/core/imagegallery/get_images/page/";
    // which pks are already in the SelectMultiple field
    var choices = function(){
       var selects = $(id_images).children();
       var pks = [];
       if(selects != null){
           var pks = [];
           $.each(selects, function(i){
               pks.push($(this).val());
           });
       }
       return pks;
    }();
    
    // images cache
    var img_cache = {by_pk: {}};
    var addToCache = function(page_num, page){
        images = {}
        $.each(page.images, function(pk, img){
            // convert each html fragment into an element
            images[pk] = $(img);
            img_cache.by_pk[pk] = images[pk];
        });
        page.images = images;
        img_cache[page_num] = page;
    }
    
    //adds image with in element ele to the current list of images
    //   and removes it from the bank of images
    var addImgToList = function(ele){
        //adds image to the select field (if it isn't in there already)
        var pk = $(ele).attr("img_pk");
        if(choices.indexOf(pk) == -1){
            var capt = $(ele).children(".caption").html();
            $("<option value=\"" + pk + "\" selected=\"selected\">" 
                + capt + "</option>")
                .appendTo("#id_images");
        }
        //fade ele and unbind its event
        $(ele).unbind().fadeTo("slow", 0.3);
        img_cache.by_pk[pk].addClass("selected");
    }
    
    //update bank of images that are current selected
    var updateCurImages = function(){
        $.each($("#id_images").val(), function(i){
            
        });
    }
    
    // take remove old images from selection list, add the ones from cache
    //    to the selection list
    var showImages = function(page_num){
        cur_page = img_cache[page_num]
        if(cur_page != null){
            //clear out the old image list
            $("ul#image-list").empty();
            //add new images and wire them to their click handlers
            $.each(cur_page["images"], function(pk, img){
                img.appendTo("ul#image-list")
                // don't wire images that are already selected
                if(!img.hasClass("selected")){
                    img.click(function(){
                        addImgToList(this);
                    });
                }
            })
            //remove old links and add new ones (and wire their ev handlers)
            $("a.images-bank").remove();
            if(cur_page.next_page != 0){
                $("<a href=\"#\" class=\"images-bank\">Older</a>")
                    .appendTo("ul#image-list")
                    .click(function(){getImages(cur_page.next_page)})
                    .append($("<span> | </span>"));
            }
            if(cur_page.prev_page != 0){
                $("<a href=\"#\" class=\"images-bank\">Newer</a>")
                    .appendTo("ul#image-list")
                    .click(function(){getImages(cur_page.prev_page)});            
            }
        }
    }
    
    // makes ajax request for images
    var getImages = function(page_num){
        // if its not in the cache, make the request and load it into the cache
        if(img_cache[page_num] == null){
            $.getJSON(image_req_url + page_num, function(json){
                //put it in the cache
                addToCache(page_num, json);
                //remove old images, add new ones
                showImages(page_num);
            })
        } else {
            showImages(page_num);
        }
    }
    
    // make first ajax request
    getImages(1);
    updateCurImages();
});