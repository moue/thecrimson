$(document).ready(function(){
	$('.rotator_preview').cycle({
	    fx:     'fade',
	    speed:  'slow',
		timeout: 5000,
	    pager:  '.rotator_carousel_contents',
	    pagerAnchorBuilder: function(idx, slide) {
	        return '<span class="pager_item"><a href="#">&bull;</a></span>';
        }
	});

    $(".rotator").hover(function (){
            $(".rotator_carousel", this).fadeIn("fast");
            $('.rotator_preview', this).cycle('pause'); 
    },function (){
            $(".rotator_carousel", this).fadeOut("fast");
            $('.rotator_preview', this).cycle('resume'); 
    });
    
});