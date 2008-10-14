$(document).ready(function (){

    // activates the remove gallery button
    var activateRemoveButton = function(){
        $("#image_gallery_remove_button")
            .show()
            .click(function(){
                // remove the gallery from the current gal area
                $("#image_gallery_current").remove();
                // remove the gallery pk from the input
                $("#id_image_gallery").val("");
                // remove any highlighting from gallery list
                $("[class*=selected]").removeClass("selected")
                deactivateRemoveButton();
                return false;
            });
    }
    
    // deactivates the remove gallery button
    var deactivateRemoveButton = function(){
        $("#image_gallery_remove_button")
            .hide().unbind();
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
                $.each(json.galleries, function(i, val){
                    galleries_returned = true;
                    val = $(val);
                    $(".image_gallery_results").append(val);
                    if(i == $("#id_image_gallery").val()){
                        // pre highlight image gallery if it is already selected
                        $(val).addClass("selected")
                    } else {
                        $(val)
                        // hover
                            .hover(function(){
                                $(val).addClass("highlighted");
                            }, function(){
                                $(val).removeClass("highlighted");
                            })
                        // when someone clicks the image gallery
                            .click(function(){
                                $(this).unbind();
                                // clear replace the current gallery area with this gallery
                                $("#image_gallery_current").remove()
                                $(".image_gallery_select").prepend(
                                    $(this)
                                        .clone()
                                        .attr("id", "image_gallery_current")
                                        .removeClass("highlighted")
                                );
                                // unset other background colors
                                $(".image_gallery_preview").removeClass("selected");
                                // set a background color
                                $(this).addClass("selected");
                                // add it to the <input>
                                $("#id_image_gallery").val(i);
                                // activate the remove button
                                activateRemoveButton();
                            });
                    }
                });
                console.log(galleries_returned);
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
                    $(".image_gallery_results").append("no image galleries found");
                }
            }
        );
    };
    
    $("#find_image_gallery_button").click(function(){
        grabImages(1);
        return false;
    });
    
    if($("#id_image_gallery").val()){
        activateRemoveButton(); 
    }
});