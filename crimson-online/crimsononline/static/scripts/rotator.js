$(document).ready(function(){
	$('.rotator_preview').cycle({
	    fx:     'fade',
	    speed:  'slow',
		timeout: 4000,
	    pager:  '.rotator_carousel_contents',
	    pagerAnchorBuilder: function(idx, slide) {
	        return '<span class="pager_item"><a href="#">&bull;</a></span>';
        }
	});

    $(".rotator").hover(function (){
            $(".rotator_carousel").fadeIn("fast");
            $('.rotator_preview').cycle('pause'); 
    },function (){
            $(".rotator_carousel").fadeOut("fast");
            $('.rotator_preview').cycle('resume'); 
    });
    
});