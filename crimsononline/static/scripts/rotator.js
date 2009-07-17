$(document).ready(function(){
	$('.preview_body').cycle({
	    fx:     'fade',
	    speed:  'slow',
		timeout: 3000,
	    pager:  '#preview_roll',
		next: '.nextbutton',
		prev: '.previousbutton',
	    pagerAnchorBuilder: function(idx, slide) {
	        return '<span class="pager_item"><a href="#">&bull;</a></span>';
        }
	});

    $(".rotator").hover(function (){
            $(".carousel").fadeIn("fast");
    },function (){
            $(".carousel").fadeOut("fast");
    });
    
});