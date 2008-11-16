$(document).ready(function(){
    var pk = 0;
    $(".imagelist li").click(function(){
        pk = $(this).attr("id").split("_")[2];
        $.get("/gallery/get_img/" + pk, function(data, textStatus){
            $(".bigimage img").replaceWith($(data));
        });
    });
});