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
                    //if(val(i)
                    // when someone clicks the image gallery, it'll be added to the dropdown
                    // TODO: add it to the preview area too
                    $(val).click(function(){
                        // set a background color
                        var assblue = "lemonchiffon";
                        $(this).css("background-color", assblue);
                        // TODO: unset other background colors
                        
                        // add it to the <input>
                        $("#id_image_gallery").val(i);
                    });
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