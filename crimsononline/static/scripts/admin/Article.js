$(document).ready(function (){

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
                // clear out the image gallery
                $(".image_gallery_results").empty();
                // add the new image galleries into the results div
                $.each(json.galleries, function(i, val){
                    val = $(val);
                    $(".image_gallery_results").append(val);
                    var assblue = "lemonchiffon";
                    if(i == $("#id_image_gallery").val()){
                        // pre highlight image gallery if it is already selected
                        $(val).css("background-color", assblue)
                    } else {
                        // when someone clicks the image gallery
                        $(val)
                        .hover(function(){
                            $(val).css("background-color", "lightgreen");
                        }, function(){
                            $(val).css("background-color", "white");
                        })
                        .click(function(){
                            $(this).unbind();
                            // TODO: unset other background colors
                            $(
                            // set a background color
                            $(this).css("background-color", assblue);
                            // add it to the <input>
                            $("#id_image_gallery").val(i);
                            // TODO: add it to the preview area too
                        });
                    }
                });
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
            }
        );
    };
    
    

    $("#find_image_gallery_button").click(function(){
	//TODO: validate fields?
        grabImages(1);
        return false;
    });
});