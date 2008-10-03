$(document).ready(function (){
    $("#find_image_gallery_button").click(function(){
	//TODO: validate fields?
        $.getJSON($.sprintf(
            "/admin/core/imagegallery/get_img_gallery/%s/%s/%s/%s/%s/",
            $("#search_by_start_year").val(),
            $("#search_by_start_month").val(),
            $("#search_by_end_year").val(),
            $("#search_by_end_month").val(),
            $("#search_by_tag").val()),
            function(json){
                $(".image_gallery_select").append(json.galleries[1]);
            }
        );
		return false;
    });
});