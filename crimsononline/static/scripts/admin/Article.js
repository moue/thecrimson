$(document).ready(function (){
    $("#find_image_gallery_button").click(function(){
        $.getJSON(String.format(
            "/admin/core/imagegallery/get_img_gallery/%s/%s/%s/%s/%s/",
            $("#search_by_start_year").val(),
            $("#search_by_start_month").val(),
            $("#search_by_end_year").val(),
            $("#search_by_end_month").val(),
            $("#search_by_tags").val()),
            function(json){
                //TODO: throw the JSON into gallery selector, bind images.click to functions
            }
        )
    });
});