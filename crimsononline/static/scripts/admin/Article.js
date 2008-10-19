// monkey patch dismiss related lookup popup to call our code
var originalDismissAddAnotherPopup = dismissAddAnotherPopup;
dismissAddAnotherPopup = function(win, newId, newRepr){
    alert("hi");
    return originalDismissAddAnotherPopup(win, newId, newRepr);
}

$(document).ready(function (){

    // activates the remove gallery button
    var activateRemoveButton = function(){
        deactivateRemoveButton();
        $("#image_gallery_remove_button")
            .show()
            .click(function(){
                // remove the gallery from the current gal area
                $("#image_gallery_current").empty();
                // remove the gallery pk from the input
                $("#id_selected_image").val("");
                // remove any highlighting from gallery list
                activateImageSelector($(".image_gallery_results [class*=selected]")
                    .removeClass("selected"));
                deactivateRemoveButton();
                return false;
            });
    }
    
    // deactivates the remove gallery button
    var deactivateRemoveButton = function(){
        $("#image_gallery_remove_button")
            .hide().unbind();
    }
    
    //
    var activateImageSelector = function(ele){
        $(ele)
            // flashy hover effect
            .hover(function(){
                $(this).addClass("highlighted");
            }, function(){
                $(this).removeClass("highlighted");
            })
            .click(function(){
                // deactivate this image selector
                $(this).removeClass("highlighted").unbind();
                // add it to the selected image <input>
                $("#id_selected_image").val($(ele).attr("id").replace("preview_",""));
                // TODO: add image type to image type <input>
                
                // replace the current gallery area with this gallery
                $("#image_gallery_current").after(
                    $(this)
                        .clone()
                        .attr("id", "image_gallery_current")
                ).remove();
                // unset other background colors
                activateImageSelector($(".image_gallery_results [class*=selected]")
                    .removeClass("selected"));
                // set a background color
                $(this).addClass("selected");
                // activate the remove button
                activateRemoveButton();
            });
    }
    
    // gets the images from the server
    var grabImages = function(page){
        $.getJSON(
            $.sprintf(
                "/admin/core/imagegallery/get_img_gallery/%s/%s/%s/%s/%s/%d/",
                $("#search_by_start_year").val(),
                $("#search_by_start_month").val(),
                $("#search_by_end_year").val(),
                $("#search_by_end_month").val(),
                $("#search_by_tag").val(),
                page),
            function(json){
                var galleries_returned = false;
                // clear out the image gallery
                $(".image_gallery_results").empty();
                // add the new image galleries into the results div
                $.each(json.galleries, function(i, gal_html){
                    galleries_returned = true;
                    
                    //var type = i.split("_")[0];
                    //var pk = i.split("_")[1];
                    gal = $(gal_html);
                    $(".image_gallery_results").append(gal);
                    if(i == $("#id_selected_image").val()){
                        // pre highlight image gallery if it is already selected
                        $(gal).addClass("selected")
                    } else {
                        activateImageSelector($(gal));
                    }
                });
                if(galleries_returned){
                    // add the pagination buttons to the end of the image galleries
                    var next_page = parseInt(json.next_page);
                    var prev_page = parseInt(json.prev_page);
                    var link_str = "<a href=\"#\" class=\"image_gallery_page_link\">%s</a>"
                    if(next_page){
                        var link = $($.sprintf(link_str, "Next"));
                        $(".image_gallery_results").append(link);
                        $(link).click(function(){
                            grabImages(next_page);
                            return false;
                        });
                    };
                    if(prev_page){
                        var link = $($.sprintf(link_str, "Prev"));
                        $(".image_gallery_results").append(link);
                        $(link).click(function(){
                            grabImages(prev_page);
                            return false;
                        });
                    };
                } else {
                    // display an error message
                    $(".image_gallery_results").append("No images matched your query");
                }
            }
        );
    };
    
    $("#find_image_gallery_button").click(function(){
        grabImages(1);
        return false;
    });
    
    if($("#id_selected_image").val()){
        activateRemoveButton(); 
    }
});