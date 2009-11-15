$(document).ready(function(){

	$('.rotator_preview').each(function (index) {
		$(this).cycle({
		    fx:     'fade',
		    speed:  'slow',
			timeout: 5000,
		    pager:  '#' + this.parentNode.id + ' .rotator_carousel_contents',
		    pagerAnchorBuilder: function(idx, slide) {
				// slide.parentNode.tagName
		        return '<span class="pager_item"><a href="#">&bull;</a></span>';
	        }
		})
	});
	

    $(".rotator").hover(function (){
            $(".rotator_carousel", this).fadeIn("fast");
            $('.rotator_preview', this).cycle('pause'); 
    },function (){
            $(".rotator_carousel", this).fadeOut("fast");
            $('.rotator_preview', this).cycle('resume'); 
    });
    
});