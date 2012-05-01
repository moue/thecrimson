$(document).ready(function(){
	//$("#glossy .glossy-big").hide();
	$("#box-hylton").click(function(){
		$(".glossy-big[id!='big-hylton']").slideUp("normal");
		$("#box-hylton img").animate({opacity:1},"fast");
		$("#big-hylton").slideToggle("normal");
		$("#big-hylton img").animate({opacity:1},"normal");
	});
	$("#box-new").click(function(){
		$(".glossy-big[id!='big-new']").slideUp("normal");
		$("#box-new img").animate({opacity:1},"fast");
		$("#big-new").slideToggle("normal");
		$("#big-new img").animate({opacity:1},"normal");
	});
	$("#box-schumacher").click(function(){
		$(".glossy-big[id!='big-schumacher']").slideUp("normal");
		$("#box-schumacher img").animate({opacity:1},"fast");
		$("#big-schumacher").slideToggle("normal");
		$("#big-schumacher img").animate({opacity:1},"normal");
	});
	$("#box-uruchurtu").click(function(){
		$(".glossy-big[id!='big-uruchurtu']").slideUp("normal");
		$("#box-uruchurtu img").animate({opacity:1},"fast");
		$("#big-uruchurtu").slideToggle("normal");
		$("#big-uruchurtu img").animate({opacity:1},"normal");
	});
	$("#box-mccaffrey").click(function(){
		$(".glossy-big[id!='big-mccaffrey']").slideUp("normal");
		$("#box-mccaffrey img").animate({opacity:1},"fast");
		$("#big-mccaffrey").slideToggle("normal");
		$("#big-mccaffrey img").animate({opacity:1},"normal");
	});
	$("#box-vaggo").click(function(){
		$(".glossy-big[id!='big-vaggo']").slideUp("normal");
		$("#box-vaggo img").animate({opacity:1},"fast");
		$("#big-vaggo").slideToggle("normal");
		$("#big-vaggo img").animate({opacity:1},"normal");
	});
	$("#box-reyes").click(function(){
		$(".glossy-big[id!='big-reyes']").slideUp("normal");
		$("#box-reyes img").animate({opacity:1},"fast");
		$("#big-reyes").slideToggle("normal");
		$("#big-reyes img").animate({opacity:1},"normal");
	});
	$("#box-baranouski").click(function(){
		$(".glossy-big[id!='big-baranouski']").slideUp("normal");
		$("#box-baranouski img").animate({opacity:1},"fast");
		$("#big-baranouski").slideToggle("normal");
		$("#big-baranouski img").animate({opacity:1},"normal");
	});
	$("#box-rodriguez").click(function(){
		$(".glossy-big[id!='big-rodriguez']").slideUp("normal");
		$("#box-rodriguez img").animate({opacity:1},"fast");
		$("#big-rodriguez").slideToggle("normal");
		$("#big-rodriguez img").animate({opacity:1},"normal");
	});
	$("#box-chakravarty").click(function(){
		$(".glossy-big[id!='big-chakravarty']").slideUp("normal");
		$("#box-chakravarty img").animate({opacity:1},"fast");
		$("#big-chakravarty").slideToggle("normal");
		$("#big-chakravarty img").animate({opacity:1},"normal");
	});
	$("#box-choi").click(function(){
		$(".glossy-big[id!='big-choi']").slideUp("normal");
		$("#box-choi img").animate({opacity:1},"fast");
		$("#big-choi").slideToggle("normal");
		$("#big-choi img").animate({opacity:1},"normal");
	});
	$("#box-jenkins").click(function(){
		$(".glossy-big[id!='big-jenkins']").slideUp("normal");
		$("#box-jenkins img").animate({opacity:1},"fast");
		$("#big-jenkins").slideToggle("normal");
		$("#big-jenkins img").animate({opacity:1},"normal");
	});
	$("#box-cheng").click(function(){
		$(".glossy-big[id!='big-cheng']").slideUp("normal");
		$("#box-cheng img").animate({opacity:1},"fast");
		$("#big-cheng").slideToggle("normal");
		$("#big-cheng img").animate({opacity:1},"normal");
	});
	$("#box-wall").click(function(){
		$(".glossy-big[id!='big-wall']").slideUp("normal");
		$("#box-wall img").animate({opacity:1},"fast");
		$("#big-wall").slideToggle("normal");
		$("#big-wall img").animate({opacity:1},"normal");
	});
	$("#box-ramsey").click(function(){
		$(".glossy-big[id!='big-ramsey']").slideUp("normal");
		$("#box-ramsey img").animate({opacity:1},"fast");
		$("#big-ramsey").slideToggle("normal");
		$("#big-ramsey img").animate({opacity:1},"normal");
	});
	$("#box-more").click(function(){
		$(".glossy-big[id!='big-more']").slideUp("normal");
		$("#box-more img").animate({opacity:1},"fast");
		$("#big-more").slideToggle("normal");
		$("#big-more img").animate({opacity:1},"normal");
	});
	
	$(".glossy-big").mouseover(function(){
		$(".glossy-big .glossy-more").fadeIn("slow");
	});
	$(".glossy-big").mouseleave(function(){
		$(".glossy-big .glossy-more").fadeOut("normal");
	});
});