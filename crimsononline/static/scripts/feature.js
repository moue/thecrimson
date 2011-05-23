/// <reference path="http://ajax.aspnetcdn.com/ajax/jQuery/jquery-1.6.1.js"/>

function DoFeatureNav(feature, section, pubStatus) {
    if (pubStatus == 1) {
        var dom = document.domain;
        document.location.href = "http://" + dom + "/feature/" + feature + "/" + section;
    } else {
        
    }
}

$("document").ready(function () {
    $("div.feature_verticalDivider").each(function () {
        $(this).css("height", $(this).parent().height() + "px");
    });
    if (video1) {
        jwplayer("mainVideoContainer").setup({
            flashplayer: swfUrl,
            file: video1,
            height: 155,
            width: 270,
            controlbar: { position: 'bottom' }
        });

        jwplayer("videoContainer1").setup({
            flashplayer: swfUrl,
            file: video2,
            height: 45,
            width: 75,
            controlbar: { position: 'none' }
        });

        jwplayer("videoContainer1").onBuffer(function () {
            document.location.href = video2url;
        });

        jwplayer("videoContainer2").setup({
            flashplayer: swfUrl,
            file: video3,
            height: 45,
            width: 75,
            controlbar: { position: 'none' }
        });

        jwplayer("videoContainer2").onBuffer(function () {
            document.location.href = video3url;
        });

        jwplayer("videoContainer3").setup({
            flashplayer: swfUrl,
            file: video4,
            height: 45,
            width: 75,
            controlbar: { position: 'none' }
        });

        jwplayer("videoContainer3").onBuffer(function () {
            document.location.href = video4url;
        });

        
    }
    $("#content_wrapper").height(($("div.feature_centerBar").height() + 200) + "px");

    if (media) {
        $("body").css("background-color", "#343233");
        window.setTimeout("$('#content_wrapper').height(($('div.feature_mediaContentSection').height() + 200) + 'px')", 1000);
        window.setTimeout("doSizeVerticals();", 1000);
        if (mainVideo) {
            jwplayer("mainVideoContainer").setup({
                flashplayer: swfUrl,
                file: mainVideo,
                height: 335,
                width: 550,
                controlbar: { position: 'bottom' }
            });
        }
    }
});

function doBuildPlayer(url, id, siteUrl) {
    jwplayer(id).setup({
        flashplayer: swfUrl,
        file: url,
        height: 95,
        width: 130,
        controlbar: { position: 'none' }
    });

    jwplayer(id).onBuffer(function () {
        document.location.href = "http://" + document.domain + siteUrl;
        jwplayer(id).stop();
    });
}

function doSizeVerticals() {
    $("div.feature_verticalDividerBlack").each(function () {
        $(this).css("height", $(this).parent().height() + "px");
    });
}