$(document).ready(function(){
    //hide the SelectMultiple field
    $("#id_images").hide();
    
    // prefix of the url from which to grab images
    var image_req_url = "/admin/core/imagegallery/get_images/";
    // which pks are already in the SelectMultiple field
    var choices = function(){
       var selects = $("#id_images").children();
       var pks = [];
       if(selects != null){
           $.each(selects, function(i){
               pks.push($(this).val());
           });
       }
       return pks;
    }();
    
    // images cache
    var img_cache = {by_pk: {}};
    var addToCache = function(page_num, page){
        var images = {}
        $.each(page.images, function(pk, img){
            // convert each html fragment into an element
            images[pk] = $(img);
            img_cache.by_pk[pk] = images[pk];
        });
        page.images = images;
        img_cache[page_num] = page;
        //testing
        $.each(img_cache.by_pk, function(i, item){
            console.log(i + "\n" + item.html());
        })
    }
    
    //adds image with in element ele to images-current
    //   and removes it from the images-bank
    var addImgToCurrent = function(ele){
        ele = $(ele);
        console.log(ele.html());
        //if the image isn't in the select field, add it
        var pk = ele.attr("img_pk");
        if(choices.indexOf(pk) == -1){
            var capt = ele.children(".caption").html();
            $("<option value=\"" + pk + "\" selected=\"selected\">" 
                + capt + "</option>")
                .appendTo("#id_images");
            //add the pk to choices
            choices.push(pk);
        // if its already there, select it
        } else {
            $("#id_images").children("[value='" + pk + "']")
                .attr("selected", "selected");
        }
        //fade ele and unbind its event; mark it as selected
        ele.unbind().fadeTo("slow", 0.3);
        img_cache.by_pk[pk].addClass("selected");
        //clone ele and add it to images-current
        ele.clone()
            .appendTo("#images-current .image-list")
            .hide()
            .click(function(){
                removeImgFromCurrent(this);
            })
            .fadeIn("slow");
    }
    
    //removes image ele from images-current and adds it back to images-bank
    var removeImgFromCurrent = function(ele){
        ele = $(ele);
        var pk = ele.attr("img_pk");
        // deselect in the select field
        $("#id_images").children("[value='" + pk + "']")
            .removeAttr("selected");
        //remove the image
        ele.fadeOut("slow", function(){
            $(this).remove();
        });
        // if its in the cache, unfade it and rebind its event handler
        img = img_cache.by_pk[pk];
        if(img != null){
            img
                .fadeTo("slow", 1.0, function(){
                    $(this).click(function(){
                        addImgToCurrent(this);
                    });
                })
                .removeClass("selected");
        }
    }
    
    // remove old images from images-bank, add the ones from cache
    var updateImagesBank = function(page_num){
        cur_page = img_cache[page_num]
        if(cur_page != null){
            //clear out the images from the images-bank
            var imglist = $("#images-bank ul.image-list");
            imglist.empty();
            //add new images and wire them to their click handlers
            $.each(cur_page["images"], function(pk, img){
                img.appendTo(imglist)
                // don't wire images that are already selected
                if(!img.hasClass("selected")){
                    img.click(function(){
                        addImgToCurrent(this);
                    });
                }
            })
            //remove old links, add new ones, and wire their ev handlers
            $("#images-bank .links").empty();
            if(cur_page.next_page != 0){
                $("<a href=\"#\">Older</a>")
                    .appendTo("#images-bank .links")
                    .click(function(){getImagesBank(cur_page.next_page)})
                    .append($("<span> | </span>"));
            }
            if(cur_page.prev_page != 0){
                $("<a href=\"#\">Newer</a>")
                    .appendTo("#images-bank .links")
                    .click(function(){getImagesBank(cur_page.prev_page)});            
            }
        }
    }
    
    // makes ajax request for images for the images-bank
    var getImagesBank = function(page_num){
        // if its not in the cache, make the request and load it into the cache
        if(img_cache[page_num] == null){
            $.getJSON(image_req_url + "page/" + page_num, function(json){
                //put it in the cache
                addToCache(page_num, json);
                //remove old images, add new ones
                updateImagesBank(page_num);
            })
        // otherwise just trigger the AJAX-received action
        } else {
            updateImagesBank(page_num);
        }
    }
    
    // makes ajax request for images for images-current
    var getImagesCur = function(){
        $.each(choices, function(i){
            // grab the image, wire its click handler
            $.get(image_req_url + "pk/" + this, function(html){
                var ele = $(html);
                var pk = ele.attr("img_pk");
                ele
                    .appendTo("#images-current .image-list")
                    .click(function(){
                        removeImgFromCurrent(this);
                    });
                // if its in the cache, fade it from images-bank
                ele = img_cache.by_pk[pk];
                if(ele != null){
                    $(ele).fadeTo("fast", 0.3).unbind();
                }
            });
        });
    }
    
    // make first ajax requests
    getImagesBank(1);
    getImagesCur();
});